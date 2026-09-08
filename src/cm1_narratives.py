"""Evidence-first CM1 commentary. All monetary inputs and thresholds are kEUR.

Attribution explains the calculated PVM effects. Residual mix is not evidence
of a particular commercial cause. This module does not change the PVM math.
"""
from dataclasses import asdict, dataclass, fields
import json
import math
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class Policy:
    eps: float = 0.5
    min_drill: float = 25.0
    concentration: float = 0.60
    divergence_abs: float = 150.0
    divergence_share: float = 0.25
    offset_ratio: float = 0.40
    toxic_ratio: float = 0.50
    subtitle_max: int = 120

    def __post_init__(self):
        for name in ('eps', 'min_drill', 'divergence_abs'):
            if not math.isfinite(getattr(self, name)) or getattr(self, name) <= 0:
                raise ValueError(f'{name} must be finite and positive')
        for name in ('concentration', 'divergence_share', 'offset_ratio', 'toxic_ratio'):
            if not 0 < getattr(self, name) <= 1:
                raise ValueError(f'{name} must be in (0, 1]')
        if not isinstance(self.subtitle_max, int) or self.subtitle_max < 80:
            raise ValueError('subtitle_max must be an integer of at least 80')


DEFAULT_POLICY = Policy()
DRIVERS = {'Price': 'Price_Segment', 'Volume': 'Volume_Segment', 'Mix': 'Mix_Segment'}


def load_policy(path=None):
    path = Path(path) if path else Path(__file__).resolve().parents[1] / 'config' / 'narrative_policy.json'
    if not path.exists():
        return DEFAULT_POLICY
    values = json.loads(path.read_text(encoding='utf-8'))
    unknown = set(values) - {f.name for f in fields(Policy)}
    if unknown:
        raise ValueError(f'Unknown narrative policy settings: {sorted(unknown)}')
    return Policy(**values)


def number(row, key):
    value = float(row[key])
    if not math.isfinite(value):
        raise ValueError(f'{key} must be finite for narrative generation')
    return value


def diagnose(row, policy=DEFAULT_POLICY):
    total = number(row, 'Total_Segment')
    effects = [{'name': name, 'value': number(row, column)} for name, column in DRIVERS.items()]
    positives = sorted((e for e in effects if e['value'] >= policy.eps), key=lambda e: (-e['value'], e['name']))
    negatives = sorted((e for e in effects if e['value'] <= -policy.eps), key=lambda e: (e['value'], e['name']))
    flat = abs(total) < policy.eps
    aligned, opposed = (positives, negatives) if total >= 0 else (negatives, positives)
    top = aligned[0] if aligned else (opposed[0] if opposed else None)
    offset = opposed[0] if opposed and aligned else None
    if flat:
        top = positives[0] if positives else (negatives[0] if negatives else None)
        offset = negatives[0] if positives and negatives else None
        pattern = 'offsetting' if positives and negatives else 'flat'
    elif top and offset and total > 0 and top['name'] == 'Price' and offset['name'] == 'Mix' and abs(offset['value']) > abs(top['value']) * policy.toxic_ratio:
        pattern = 'toxic'
    elif top and offset and {top['name'], offset['name']} == {'Price', 'Volume'} and number(row, 'Volume_Segment') >= policy.eps and number(row, 'Price_Segment') < -policy.toxic_ratio * number(row, 'Volume_Segment'):
        pattern = 'price_volume_tradeoff'
    elif top and offset and abs(offset['value']) > abs(top['value']) * policy.offset_ratio:
        pattern = 'tradeoff'
    elif total < 0 and len(negatives) >= 2 and not positives:
        pattern = 'broad_decline'
    else:
        pattern = 'simple'
    return {'total': total, 'top': top, 'offset': offset, 'pattern': pattern,
            'positives': positives, 'negatives': negatives,
            'effects': effects, 'policy': asdict(policy), 'reconciliation_gap': total - sum(e['value'] for e in effects)}


def clean_details(details):
    """Use leaf rows; consolidate additive records by their full hierarchy key."""
    data = details.copy()
    if 'Rollup_Level' in data:
        data = data[pd.to_numeric(data['Rollup_Level'], errors='coerce') == 2]
    if '_is_plug' in data:
        plug = data['_is_plug'].map(lambda v: str(v).strip().lower() in ('true', '1', '1.0'))
        data = data[~plug]
    if data.empty:
        return data
    data['Total_Segment'] = pd.to_numeric(data['Base_CM1'], errors='raise') - pd.to_numeric(data['Comp_CM1'], errors='raise')
    for col in ['Total_Segment', *DRIVERS.values()]:
        if col in data:
            data[col] = pd.to_numeric(data[col], errors='raise')
            if not data[col].map(math.isfinite).all():
                raise ValueError(f'Non-finite detail {col}')
    # Country identity remains distinct when a consolidated regional view is used.
    if 'ViewName_Orig' in data:
        data['ViewName'] = data['ViewName_Orig']
    keys = [c for c in ('ViewName', 'Final_Segment', 'SlideSubSegment') if c in data]
    for key in keys:
        data[key] = data[key].fillna('Unspecified').astype(str)
    values = [c for c in ('Base_CM1', 'Comp_CM1', 'Total_Segment', *DRIVERS.values()) if c in data]
    return data.groupby(keys, as_index=False, dropna=False, sort=True)[values].sum()


def select_hierarchy(details, metric, sign, levels, policy=DEFAULT_POLICY, gross_total=None):
    """Drill only while a branch explains a material share of one signed effect.

    The denominator is gross same-sign leaf movement in the full scope, never
    the net country variance or a successively shrinking parent denominator.
    """
    result = {'path': [], 'level': 'scope', 'value': 0.0, 'share': 0.0, 'reason': 'distributed'}
    if details.empty or metric not in details or not sign:
        result['reason'] = 'no_material_detail'
        return result
    valid = details.copy()
    values = pd.to_numeric(valid[metric], errors='raise')
    if not values.map(math.isfinite).all():
        raise ValueError(f'Non-finite detail {metric}')
    valid[metric] = values
    gross = float(values[values * sign > 0].abs().sum())
    if gross_total is not None:
        gross = max(gross, gross_total)
    if gross < policy.min_drill:
        result['reason'] = 'below_materiality'
        return result
    current = valid
    for level in levels:
        if level not in current:
            break
        groups = current.groupby(level, dropna=False, sort=True)[metric].sum().reset_index()
        groups = groups[groups[metric] * sign > 0].copy()
        if groups.empty:
            break
        groups['_abs'] = groups[metric].abs()
        groups['_label'] = groups[level].fillna('Unspecified').astype(str)
        groups = groups.sort_values(['_abs', '_label'], ascending=[False, True], kind='stable')
        lead = groups.iloc[0]
        share = float(lead['_abs'] / gross)
        if lead['_abs'] < policy.min_drill or share < policy.concentration:
            break
        label = lead['_label']
        result = {'path': result['path'] + [(level, label)], 'level': level,
                  'value': float(lead[metric]), 'share': share, 'reason': 'concentrated'}
        current = current[current[level].fillna('Unspecified').astype(str) == label]
    return result


def _divergence(details, policy, levels=None):
    """Bubble material opposing branches up even if their parent net is small."""
    if details.empty:
        return None
    levels = levels or [c for c in ('Final_Segment', 'SlideSubSegment') if c in details]
    levels = [c for c in levels if c in details]
    winners = []
    for sign in (1, -1):
        gross = float(details.loc[details['Total_Segment'] * sign > 0, 'Total_Segment'].abs().sum())
        candidates = []
        for depth in range(1, len(levels) + 1):
            keys = levels[:depth]
            grouped = details.groupby(keys, as_index=False, sort=True)['Total_Segment'].sum()
            for _, item in grouped.iterrows():
                value = float(item['Total_Segment'])
                if value * sign < policy.divergence_abs or not gross or abs(value) / gross < policy.divergence_share:
                    continue
                candidates.append({'path': [(k, str(item[k])) for k in keys], 'value': value})
        if not candidates:
            return None
        # Most specific supported branch, with stable monetary/label tie-breaks.
        candidates.sort(key=lambda c: (-len(c['path']), -abs(c['value']), str(c['path'])))
        winners.append(candidates[0])
    return {'growth': winners[0], 'decline': winners[1]}


def build_evidence(row, details, filter_col='ViewName', label_col='ViewName', policy=DEFAULT_POLICY):
    diagnosis = diagnose(row, policy)
    result = {'diagnosis': diagnosis, 'primary': None, 'offset': None,
              'divergence': None, 'detail_gap': None}
    if details is None:
        return result
    scope = details[details[filter_col] == row[filter_col]].copy()
    # Measure omitted reconciliation separately; never assign it to a product.
    leaf = scope if 'Rollup_Level' not in scope else scope[scope['Rollup_Level'] == 2]
    result['detail_gap'] = diagnosis['total'] - float((leaf['Base_CM1'] - leaf['Comp_CM1']).sum())
    clean = clean_details(scope)
    with_plugs = clean_details(scope.assign(_is_plug=False))
    if 'ViewName_Orig' in scope:
        levels = ['ViewName', 'Final_Segment', 'SlideSubSegment']
    elif filter_col == 'Final_Segment':
        levels = ['ViewName', 'SlideSubSegment']
    else:
        levels = ['Final_Segment', 'SlideSubSegment']
    for name, effect in [('primary', diagnosis['top']), ('offset', diagnosis['offset'])]:
        if effect:
            metric = DRIVERS[effect['name']]
            sign = 1 if effect['value'] > 0 else -1
            # Keep excluded plugs in the attribution denominator; otherwise a
            # tiny product could appear to explain a plug-dominated effect.
            gross_total = float(with_plugs.loc[with_plugs[metric] * sign > 0, metric].abs().sum()) if metric in with_plugs else None
            item = select_hierarchy(clean, metric, sign, levels, policy, gross_total)
            item['metric'] = effect['name']
            result[name] = item
    # At regional level, compare products across markets after summing each
    # complete product key. Within one country the country key is constant.
    result['divergence'] = _divergence(clean, policy, levels)
    if not clean.empty:
        result['unattributed_delta'] = diagnosis['total'] - float(clean['Total_Segment'].sum())
    else:
        result['unattributed_delta'] = diagnosis['total']
    return result


def _path_text(item):
    return ' / '.join(label for _, label in item['path'])


def render_story(evidence, label, formatter):
    diag = evidence['diagnosis']
    total = diag['total']
    effects = diag['effects']
    order = sorted(effects, key=lambda e: (-abs(e['value']), e['name']))
    policy = Policy(**diag['policy'])
    material = [e for e in order if abs(e['value']) >= policy.eps]
    # Preserve all material effects; a stylistic template cannot suppress a risk.
    terms = [f"{'residual mix' if e['name'] == 'Mix' else e['name'].lower()} {formatter(e['value'])}" for e in material]
    if diag['pattern'] == 'offsetting':
        head = f'{label}: broadly flat CM1 ({formatter(total)}) masks offsetting movements'
    else:
        head = f'{label}: CM1 {formatter(total)}'
    pattern = diag['pattern']
    if pattern == 'toxic':
        relationship = 'price gains partly offset by negative residual mix'
    elif pattern == 'price_volume_tradeoff':
        p_value = next(e['value'] for e in effects if e['name'] == 'Price')
        v_value = next(e['value'] for e in effects if e['name'] == 'Volume')
        relationship = ('volume gains outweighed by price pressure' if abs(p_value) > v_value
                        else 'volume gains partly offset by price pressure')
    elif pattern == 'tradeoff':
        top, offset = diag['top'], diag['offset']
        relationship = (f"{top['name'].lower()} {'gains' if top['value'] > 0 else 'declines'} partly offset by "
                        f"{offset['name'].lower()} {'gains' if offset['value'] > 0 else 'declines'}")
    elif pattern == 'broad_decline':
        relationship = 'multiple negative PVM effects'
    else:
        relationship = ''
    if relationship:
        story = f"{head}; {relationship} ({', '.join(terms)})."
    else:
        story = f"{head}: {', '.join(terms)}."

    if not material:
        story = f'{label}: CM1 {formatter(total)}; no material net PVM movement.'

    for field in ('primary', 'offset'):
        item = evidence.get(field)
        if item and item['path']:
            side = 'gains' if item['value'] > 0 else 'declines'
            story += f" {item['metric']} led by {_path_text(item)} ({formatter(item['value'])}; {item['share']:.0%} of {side})."
    divergence = evidence.get('divergence')
    covered = {(tuple(item['path']), item['value']) for item in
               (evidence.get('primary'), evidence.get('offset')) if item and item['path']}
    if divergence and not all((tuple(item['path']), item['value']) in covered for item in divergence.values()):
        gain, loss = divergence['growth'], divergence['decline']
        story += f" Offsetting contributions: {_path_text(gain)} gained {formatter(gain['value'])}, while {_path_text(loss)} declined {formatter(loss['value'])}."
    gap = evidence.get('unattributed_delta', 0)
    if abs(gap) >= policy.min_drill:
        story += f' Reconciliation / unallocated movement {formatter(gap)} is excluded from product attribution.'
    return story


def render_subtitle(diag, formatter, max_len=120):
    material = sorted((e for e in diag['effects'] if abs(e['value']) >= diag['policy']['eps']), key=lambda e: (-abs(e['value']), e['name']))
    if not material:
        return f"CM1 {formatter(diag['total'])}; no material net PVM movement."
    prefix = f"CM1 {formatter(diag['total'])}" + (' (offsetting)' if diag['pattern'] == 'offsetting' else '')
    effects = '; '.join(f"{e['name']} {formatter(e['value'])}" for e in material)
    text = f'{prefix}; {effects}.'
    if len(text) > max_len:
        # Drop wording, never cut a value or omit an opposing effect.
        text = f"Net {formatter(diag['total'])}; " + '; '.join(f"{e['name'][0]} {formatter(e['value'])}" for e in material) + '.'
    if len(text) > max_len:
        raise ValueError('Subtitle exceeds the configured limit')
    return text


def regional_bullets(segments, formatter, top_n=5, policy=DEFAULT_POLICY):
    """Select both signed tails by magnitude and use the same PVM evidence."""
    sections = []
    eligible = segments[~segments['Final_Segment'].str.contains(r'Misc|Unmapped', case=False, na=False)].copy()
    eligible['_abs'] = eligible['Total_Segment'].abs()
    for title, sign in [('Upsides', 1), ('Challenges', -1)]:
        group = eligible[eligible['Total_Segment'] * sign > 0].sort_values(['_abs', 'Final_Segment'], ascending=[False, True], kind='stable').head(top_n)
        lines = []
        for _, row in group.iterrows():
            diag = diagnose(row, policy)
            lines.append(f"{row['Final_Segment']} {render_subtitle(diag, formatter)}")
        if lines:
            sections.append(title + '\n' + '\n'.join(lines))
    return '\n\n'.join(sections)
