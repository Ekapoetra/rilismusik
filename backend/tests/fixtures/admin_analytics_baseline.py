# Read-only regression oracle from 4ffcf8847f267adbb55d614f5105d6c56ec62cb7; do not update to match new code.
async def admin_monthly_analytics(user: dict=Depends(require_admin), period_from: Optional[str]=Query(None, description='Inclusive — YYYY-MM'), period_to: Optional[str]=Query(None, description='Inclusive — YYYY-MM'), label_id: Optional[str]=Query(None), platform: Optional[str]=Query(None), country: Optional[str]=Query(None), artist_id: Optional[str]=Query(None), track_id: Optional[str]=Query(None), top_n: int=Query(10, ge=1, le=50)):
    """Single-call dashboard payload — KPI + monthly revenue + top-N per dim.

    When a `*_id` / dimension filter is given, the cached `monthly_analytics`
    collection no longer has the right pre-aggregation (it's grouped on the raw
    line), so we fall back to a live aggregate over `royalty_lines` (filtered,
    still fast thanks to compound indexes). For the un-filtered case the cache
    is used directly → ~50ms response.
    """

    def _valid_period(p: Optional[str]) -> bool:
        if not p:
            return False
        if len(p) != 7 or p[4] != '-':
            return False
        try:
            int(p[:4])
            int(p[5:7])
            return True
        except ValueError:
            return False
    period_filter: Dict[str, Any] = {}
    if _valid_period(period_from):
        period_filter['$gte'] = period_from
    if _valid_period(period_to):
        period_filter['$lte'] = period_to
    has_runtime_filter = any([label_id, platform, country, artist_id, track_id])
    if has_runtime_filter:
        line_match: Dict[str, Any] = analytics_eligible_filter()
        if period_filter:
            line_match['period'] = period_filter
        if label_id:
            line_match['label_id'] = label_id
        if platform:
            line_match['platform'] = platform
        if country:
            line_match['country'] = country
        if artist_id:
            line_match['artist_id'] = artist_id
        if track_id:
            line_match['track_id'] = track_id
        kpi_pipeline = [{'$match': line_match}, {'$group': {'_id': None, 'revenue_eur': {'$sum': '$revenue_eur'}, 'revenue_idr': {'$sum': '$label_idr'}, 'quantity': {'$sum': '$quantity'}, 'lines_count': {'$sum': 1}, 'distinct_platforms': {'$addToSet': '$platform'}, 'distinct_countries': {'$addToSet': '$country'}, 'distinct_tracks': {'$addToSet': '$track_id'}, 'distinct_artists': {'$addToSet': '$artist_id'}, 'distinct_labels': {'$addToSet': '$label_id'}}}]
        kpi_doc = None
        async for r in db_bg.royalty_lines.aggregate(kpi_pipeline, allowDiskUse=True):
            kpi_doc = r
        monthly_pipeline = [{'$match': line_match}, {'$group': {'_id': '$period', 'revenue_eur': {'$sum': '$revenue_eur'}, 'revenue_idr': {'$sum': '$label_idr'}}}, {'$sort': {'_id': 1}}]
        monthly = [{'period': r['_id'], 'revenue_eur': round(r['revenue_eur'], 4), 'revenue_idr': int(r['revenue_idr'])} async for r in db_bg.royalty_lines.aggregate(monthly_pipeline, allowDiskUse=True)]

        async def _topn(group_field: str, hydrate_coll: Optional[str], hydrate_field: Optional[str]):
            pipeline = [{'$match': line_match}, {'$group': {'_id': group_field, 'revenue_eur': {'$sum': '$revenue_eur'}, 'revenue_idr': {'$sum': '$label_idr'}, 'lines': {'$sum': 1}}}, {'$match': {'_id': {'$ne': None}}}, {'$sort': {'revenue_idr': -1}}, {'$limit': top_n}]
            rows = [r async for r in db_bg.royalty_lines.aggregate(pipeline, allowDiskUse=True)]
            if hydrate_coll and hydrate_field and rows:
                ids = [r['_id'] for r in rows]
                names = {}
                async for d in db_bg[hydrate_coll].find({'id': {'$in': ids}}, {'_id': 0, 'id': 1, hydrate_field: 1}):
                    names[d['id']] = d.get(hydrate_field) or '(unknown)'
                for r in rows:
                    r['name'] = names.get(r['_id'], '(unknown)')
            else:
                for r in rows:
                    r['name'] = r['_id']
            return [{'key': r['_id'], 'name': r['name'], 'revenue_eur': round(r['revenue_eur'], 4), 'revenue_idr': int(r['revenue_idr']), 'lines': int(r['lines'])} for r in rows]
        top_platforms = await _topn('$platform', None, None)
        top_countries = await _topn('$country', None, None)
        top_labels = await _topn('$label_id', 'labels', 'label_name')
        top_artists = await _topn('$artist_id', 'artists', 'artist_name')
        top_tracks = await _topn('$track_id', 'tracks', 'track_title')
        kpi = {'total_revenue_eur': round((kpi_doc or {}).get('revenue_eur') or 0, 4), 'total_revenue_idr': int((kpi_doc or {}).get('revenue_idr') or 0), 'total_quantity': int((kpi_doc or {}).get('quantity') or 0), 'total_lines': int((kpi_doc or {}).get('lines_count') or 0), 'distinct_platforms': len([p for p in (kpi_doc or {}).get('distinct_platforms') or [] if p]), 'distinct_countries': len([p for p in (kpi_doc or {}).get('distinct_countries') or [] if p]), 'distinct_tracks': len([p for p in (kpi_doc or {}).get('distinct_tracks') or [] if p]), 'distinct_artists': len([p for p in (kpi_doc or {}).get('distinct_artists') or [] if p]), 'distinct_labels': len([p for p in (kpi_doc or {}).get('distinct_labels') or [] if p])}
        return {'source': 'live', 'filters': {'period_from': period_from, 'period_to': period_to, 'label_id': label_id, 'platform': platform, 'country': country, 'artist_id': artist_id, 'track_id': track_id}, 'kpi': kpi, 'monthly': monthly, 'top_platforms': top_platforms, 'top_countries': top_countries, 'top_labels': top_labels, 'top_artists': top_artists, 'top_tracks': top_tracks}
    cache_match: Dict[str, Any] = {}
    if period_filter:
        cache_match['period'] = period_filter
    kpi_pipeline = [{'$match': {**cache_match, 'dim': 'total'}}, {'$group': {'_id': None, 'revenue_eur': {'$sum': '$revenue_eur'}, 'revenue_idr': {'$sum': '$revenue_idr'}, 'lines_count': {'$sum': '$lines_count'}, 'quantity': {'$sum': '$quantity'}}}]
    kpi_doc = None
    async for r in db_bg.monthly_analytics.aggregate(kpi_pipeline):
        kpi_doc = r
    monthly_pipeline = [{'$match': {**cache_match, 'dim': 'total'}}, {'$sort': {'period': 1}}, {'$project': {'_id': 0, 'period': 1, 'revenue_eur': 1, 'revenue_idr': 1}}]
    monthly = [r async for r in db_bg.monthly_analytics.aggregate(monthly_pipeline)]

    async def _distinct_count(dim: str) -> int:
        pipe = [{'$match': {**cache_match, 'dim': dim}}, {'$group': {'_id': '$key'}}, {'$count': 'n'}]
        async for r in db_bg.monthly_analytics.aggregate(pipe):
            return int(r.get('n') or 0)
        return 0
    distinct_platforms = await _distinct_count('platform')
    distinct_countries = await _distinct_count('country')
    distinct_labels = await _distinct_count('label')
    distinct_artists = await _distinct_count('artist')
    distinct_tracks = await _distinct_count('track')

    async def _top_from_cache(dim: str, name_field: Optional[str]):
        pipe = [{'$match': {**cache_match, 'dim': dim}}, {'$group': {'_id': '$key', 'revenue_eur': {'$sum': '$revenue_eur'}, 'revenue_idr': {'$sum': '$revenue_idr'}, 'lines': {'$sum': '$lines_count'}, 'name': {'$first': f'${name_field}'} if name_field else {'$first': '$key'}}}, {'$sort': {'revenue_idr': -1}}, {'$limit': top_n}]
        return [{'key': r['_id'], 'name': r.get('name') or r['_id'], 'revenue_eur': round(r['revenue_eur'], 4), 'revenue_idr': int(r['revenue_idr']), 'lines': int(r['lines'])} async for r in db_bg.monthly_analytics.aggregate(pipe)]
    top_platforms = await _top_from_cache('platform', None)
    top_countries = await _top_from_cache('country', None)
    top_labels = await _top_from_cache('label', 'label_name')
    top_artists = await _top_from_cache('artist', 'artist_name')
    top_tracks = await _top_from_cache('track', 'track_title')
    kpi = {'total_revenue_eur': round((kpi_doc or {}).get('revenue_eur') or 0, 4), 'total_revenue_idr': int((kpi_doc or {}).get('revenue_idr') or 0), 'total_quantity': int((kpi_doc or {}).get('quantity') or 0), 'total_lines': int((kpi_doc or {}).get('lines_count') or 0), 'distinct_platforms': distinct_platforms, 'distinct_countries': distinct_countries, 'distinct_tracks': distinct_tracks, 'distinct_artists': distinct_artists, 'distinct_labels': distinct_labels}
    return {'source': 'cache', 'cache_meta': {'finished_at': _last_recompute_meta.get('finished_at'), 'doc_count': _last_recompute_meta.get('doc_count', 0)}, 'filters': {'period_from': period_from, 'period_to': period_to, 'label_id': None, 'platform': None, 'country': None, 'artist_id': None, 'track_id': None}, 'kpi': kpi, 'monthly': monthly, 'top_platforms': top_platforms, 'top_countries': top_countries, 'top_labels': top_labels, 'top_artists': top_artists, 'top_tracks': top_tracks}
