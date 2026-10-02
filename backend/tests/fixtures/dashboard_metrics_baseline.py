# Read-only regression oracle from 4ffcf8847f267adbb55d614f5105d6c56ec62cb7; do not update to match new code.
def _period_windows(period: str):
    """Return (cur_start, cur_end, prev_start, prev_end) as UTC ISO strings."""
    now = datetime.now(timezone.utc)
    wib_now = now + WIB
    if period == 'week':
        wib_start = (wib_now - timedelta(days=wib_now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'month':
        wib_start = wib_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        wib_start = wib_now.replace(hour=0, minute=0, second=0, microsecond=0)
    cur_start = wib_start - WIB
    cur_len = now - cur_start
    prev_start = cur_start - cur_len
    return (cur_start.isoformat(), now.isoformat(), prev_start.isoformat(), cur_start.isoformat())

def _trend(cur: float, prev: float):
    if prev <= 0:
        direction = 'up' if cur > 0 else 'flat'
        return {'direction': direction, 'pct': None, 'delta': cur - prev}
    pct = round((cur - prev) / prev * 100, 1)
    return {'direction': 'up' if pct > 0 else 'down' if pct < 0 else 'flat', 'pct': pct, 'delta': cur - prev}

async def _sum(coll, match, field='amount'):
    cur = db[coll].aggregate([{'$match': match}, {'$group': {'_id': None, 's': {'$sum': f'${field}'}}}])
    async for r in cur:
        return float(r.get('s') or 0)
    return 0.0

async def _count(coll, match):
    return await db[coll].count_documents(match)

def _period_windows_dt(period: str):
    """Same windows as _period_windows but returns tz-aware datetimes (for date-typed comparisons)."""
    now = datetime.now(timezone.utc)
    wib_now = now + WIB
    if period == 'week':
        wib_start = (wib_now - timedelta(days=wib_now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'month':
        wib_start = wib_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        wib_start = wib_now.replace(hour=0, minute=0, second=0, microsecond=0)
    cur_start = wib_start - WIB
    cur_len = now - cur_start
    prev_start = cur_start - cur_len
    return (cur_start, now, prev_start, cur_start)

async def _est(coll):
    """Fast collection total (metadata count) — never blocks the dashboard on large collections."""
    try:
        return await db[coll].estimated_document_count()
    except Exception:
        return 0

async def _count_fast(coll, match, ms=4000):
    try:
        return await db[coll].count_documents(match, maxTimeMS=ms)
    except Exception:
        return 0

async def _sum_by_date(coll, base_match, date_field, cs_dt, ce_dt, field='amount_idr'):
    """Sum `field` where the (string or date) `date_field` falls in [cs_dt, ce_dt]. Robust to mixed formats."""
    try:
        cur = db[coll].aggregate([{'$match': base_match}, {'$set': {'_d': {'$convert': {'input': f'${date_field}', 'to': 'date', 'onError': None, 'onNull': None}}}}, {'$match': {'_d': {'$gte': cs_dt, '$lte': ce_dt}}}, {'$group': {'_id': None, 's': {'$sum': {'$ifNull': [f'${field}', 0]}}}}], maxTimeMS=6000)
        async for r in cur:
            return float(r.get('s') or 0)
    except Exception:
        return 0.0
    return 0.0

async def _withdrawal_total(cs_dt, ce_dt):
    """Requested withdrawal = paid (by paid_date) + pending (requested/approved by request_date).
    Mirrors the canonical Arus Dana Withdrawal cashflow so numbers match the Withdraw page."""
    paid = await _sum_by_date('withdraw_requests', {'status': 'paid'}, 'paid_date', cs_dt, ce_dt)
    pending = await _sum_by_date('withdraw_requests', {'status': {'$in': ['requested', 'approved']}}, 'request_date', cs_dt, ce_dt)
    return paid + pending

async def _latest_royalty_income():
    """Royalty income = total EUR of the most recently imported CSV, converted to IDR at its own rate."""
    proj = {'_id': 0, 'total_revenue_eur': 1, 'exchange_rate_eur_idr': 1, 'period': 1, 'filename': 1, 'created_at': 1}
    imp = await db.royalty_imports.find_one({'total_revenue_eur': {'$gt': 0}}, proj, sort=[('created_at', -1)])
    if not imp:
        return {'value': 0, 'currency': 'IDR', 'eur': 0, 'rate': 0, 'period': None, 'filename': None, 'trend': _trend(0, 0)}
    eur = float(imp.get('total_revenue_eur') or 0)
    rate = float(imp.get('exchange_rate_eur_idr') or 0)
    idr = round(eur * rate)
    prev = await db.royalty_imports.find_one({'total_revenue_eur': {'$gt': 0}, 'created_at': {'$lt': imp.get('created_at')}}, proj, sort=[('created_at', -1)])
    prev_idr = round(float(prev.get('total_revenue_eur') or 0) * float(prev.get('exchange_rate_eur_idr') or 0)) if prev else 0
    return {'value': idr, 'currency': 'IDR', 'eur': round(eur, 2), 'rate': rate, 'period': imp.get('period'), 'filename': imp.get('filename'), 'trend': _trend(idr, prev_idr)}

async def dashboard_metrics(period: str=Query('today'), user: dict=Depends(require_admin)):
    cs, ce, ps, pe = _period_windows(period)
    cs_dt, ce_dt, ps_dt, pe_dt = _period_windows_dt(period)
    can_withdraw = has_permission(user, 'withdraw.view') or user.get('role') == 'super_admin'
    can_royalty = has_permission(user, 'royalty.view') or has_permission(user, 'analytics.view') or user.get('role') == 'super_admin'
    out = {'period': period}
    sr_cur = await _sum('payments', {'provider': 'xendit', 'status': 'paid', 'paid_at': {'$gte': cs, '$lte': ce}})
    sr_prev = await _sum('payments', {'provider': 'xendit', 'status': 'paid', 'paid_at': {'$gte': ps, '$lt': pe}})
    out['sales_revenue'] = {'value': sr_cur, 'currency': 'IDR', 'trend': _trend(sr_cur, sr_prev)}
    for key, coll in (('total_labels', 'labels'), ('total_artists', 'artists'), ('total_releases', 'releases')):
        total = await _est(coll)
        added_cur = await _count_fast(coll, {'created_at': {'$gte': cs, '$lte': ce}})
        added_prev = await _count_fast(coll, {'created_at': {'$gte': ps, '$lt': pe}})
        out[key] = {'value': total, 'added': added_cur, 'trend': _trend(added_cur, added_prev)}
    active_match = {'account_status': 'active', 'blacklisted': {'$ne': True}}
    active_total = await _count_fast('labels', active_match, ms=5000)
    am_cur = await _count_fast('labels', {**active_match, 'created_at': {'$gte': cs, '$lte': ce}})
    am_prev = await _count_fast('labels', {**active_match, 'created_at': {'$gte': ps, '$lt': pe}})
    out['active_members'] = {'value': active_total, 'added': am_cur, 'trend': _trend(am_cur, am_prev)}
    if can_withdraw:
        wd_cur = await _withdrawal_total(cs_dt, ce_dt)
        wd_prev = await _withdrawal_total(ps_dt, pe_dt)
        out['requested_withdrawal'] = {'value': wd_cur, 'currency': 'IDR', 'trend': _trend(wd_cur, wd_prev)}
    if can_royalty:
        out['royalty_income'] = await _latest_royalty_income()
    out['finance_visible'] = can_withdraw or can_royalty
    return out
