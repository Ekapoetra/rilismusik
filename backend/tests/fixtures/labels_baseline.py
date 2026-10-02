# Read-only regression oracle from 4ffcf8847f267adbb55d614f5105d6c56ec62cb7; do not update to match new code.
async def label_dashboard(user: dict=Depends(require_label)):
    label = await get_label_by_user(user)
    from .balance_utils import compute_label_balance_snapshot
    balance = await compute_label_balance_snapshot(label_id=label['id'], label=label)
    total_releases = await db.releases.count_documents({'label_id': label['id']})
    active_releases = await db.releases.count_documents({'label_id': label['id'], 'status': {'$in': ['approved', 'delivered', 'live']}})
    total_tracks = await db.tracks.count_documents({'label_id': label['id']})
    total_artists = await db.artists.count_documents({'label_id': label['id']})
    active_tickets = await db.support_tickets.count_documents({'label_id': label['id'], 'status': {'$nin': ['done', 'rejected']}})
    pending_invoices = await db.payments.count_documents({'label_id': label['id'], 'status': 'pending'})
    last_revenue = 0
    last_period = None
    from .deps import db_bg
    pipeline = [{'$match': {'label_id': label['id'], 'status': {'$in': ['pending', 'available']}, 'legacy_settled': {'$ne': True}, **({'period': {'$gt': label.get('last_withdrawn_period')}} if label.get('last_withdrawn_period') else {})}}, {'$group': {'_id': '$period', 'total': {'$sum': '$label_idr'}}}, {'$sort': {'_id': -1}}, {'$limit': 1}]
    async for row in db_bg.royalty_lines.aggregate(pipeline, allowDiskUse=True):
        last_revenue = int(row.get('total') or 0)
        last_period = row.get('_id')
        break
    pipeline_counts = {'draft': 0, 'review': 0, 'delivered': 0, 'live': 0}
    _bucket = {'draft': 'draft', 'submitted': 'review', 'under_review': 'review', 'awaiting_payment': 'review', 'paid': 'review', 'approved': 'review', 'need_revision': 'review', 'delivered': 'delivered', 'live': 'live'}
    async for row in db.releases.aggregate([{'$match': {'label_id': label['id']}}, {'$group': {'_id': '$status', 'count': {'$sum': 1}}}]):
        bucket = _bucket.get(row.get('_id'))
        if bucket:
            pipeline_counts[bucket] += int(row.get('count') or 0)
    from datetime import timedelta as _td
    today_wib = (datetime.now(timezone.utc) + _td(hours=7)).date().isoformat()
    live_today = []
    for r in await db.releases.find({'label_id': label['id'], 'status': 'live', 'live_at': {'$ne': None}}, {'_id': 0, 'id': 1, 'release_title': 1, 'primary_artist_name': 1, 'artist_name': 1, 'display_cover_url': 1, 'cover_url': 1, 'live_at': 1}).sort('live_at', -1).to_list(20):
        live_at = str(r.get('live_at') or '')
        try:
            live_date = (datetime.fromisoformat(live_at.replace('Z', '+00:00')) + _td(hours=7)).date().isoformat()
        except Exception:
            continue
        if live_date == today_wib:
            live_today.append({'id': r['id'], 'release_title': r.get('release_title'), 'artist_name': r.get('primary_artist_name') or r.get('artist_name'), 'cover_url': r.get('display_cover_url') or r.get('cover_url')})
    from .kyc_service import compute_kyc_state
    return {'label': {**redact_label_for_self(label), 'kyc': await compute_kyc_state(user=user, label=label)}, 'pipeline': pipeline_counts, 'live_today': live_today, 'stats': {'balance_available_idr': balance['balance_available_idr'], 'balance_pending_idr': balance['balance_pending_idr'], 'balance_withdraw_requested_idr': balance['balance_withdraw_requested_idr'], 'last_withdrawn_period': balance['last_withdrawn_period'], 'latest_report_period': balance['latest_report_period'], 'balance_source': 'royalty_lines_and_adjustments', 'last_month_revenue_idr': last_revenue, 'last_month_period': last_period, 'total_releases': total_releases, 'active_releases': active_releases, 'total_tracks': total_tracks, 'total_artists': total_artists, 'active_tickets': active_tickets, 'pending_invoices': pending_invoices, 'subscription_status': label.get('subscription_status'), 'subscription_expires_at': label.get('subscription_expires_at'), 'contract_status': label.get('contract_status'), 'account_status': label.get('account_status'), 'bank_verified': label.get('bank_verified', False), 'payment_type': label.get('payment_type')}}
