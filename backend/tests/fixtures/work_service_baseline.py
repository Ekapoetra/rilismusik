# Read-only regression oracle from 4ffcf8847f267adbb55d614f5105d6c56ec62cb7; do not update to match new code.
async def reconcile_work(force: bool=False) -> None:
    if not force and time.time() - _RECON['at'] < 8:
        return
    _RECON['at'] = time.time()
    cache: Dict[str, Any] = {}
    for wt in WORK_TYPES:
        key = wt['key']
        current = await _sources(key)
        current_keys = set()
        for it in current:
            dk = f"{key}:{it['source']}:{it['entity_id']}"
            current_keys.add(dk)
            await db.work_items.update_one({'dedupe_key': dk, 'status': 'open'}, {'$setOnInsert': {'id': new_id(), 'dedupe_key': dk, 'work_type': key, 'source': it['source'], 'entity_id': it['entity_id'], 'entity_ref': it.get('ref'), 'label_id': it.get('label_id'), 'label_name': it.get('label_name'), 'status': 'open', 'opened_at': it['opened_at'], 'created_at': now_iso()}}, upsert=True)
        async for wi in db.work_items.find({'work_type': key, 'status': 'open'}, {'_id': 0}):
            if wi['dedupe_key'] in current_keys:
                continue
            actor, at, action = await _resolve_completion(wi['source'], wi['entity_id'])
            info = await _actor_info(actor, cache)
            await db.work_items.update_one({'id': wi['id'], 'status': 'open'}, {'$set': {'status': 'completed', 'completed_by': actor, 'completed_by_name': info['name'], 'completed_by_super': info['super'], 'completed_at': at or now_iso(), 'completion_action': action, 'updated_at': now_iso()}})

async def work_queue(scope: str='my', user: dict=Depends(require_admin)):
    """Work ownership model (PRD 'Work Scope, not Responsibility'):
      - AUTHORIZATION (has_permission) says what a user MAY do — NOT what they own.
      - scope=super_admin_only  -> belongs to Super Admin's "My Work" only (never team).
      - scope=permission        -> belongs to a regular admin's "My Work" iff that admin's
        REAL stored role permissions include the work's permission; for Super Admin it is
        team work (Team Monitor), never auto-owned via the super wildcard.
    Invariant: My Work ∩ Team Monitor = ∅ (per user). No Responsibility / gaps concept."""
    assert_admin_permission(user, 'work.view')
    await reconcile_work()
    settings = await get_work_settings()
    is_super = user.get('role') == SUPER_ADMIN_ROLE_ID
    is_manage = has_permission(user, 'work.manage')
    real_perms = set() if is_super else set(user.get('permissions') or [])
    if scope == 'team' and (not (is_manage or is_super)):
        raise HTTPException(status_code=403, detail='Hanya pengelola yang dapat melihat Team Monitor')
    delegated_perms = await _delegated_permissions()

    def is_delegated(wt: Dict[str, Any]) -> bool:
        return wt['scope'] == 'permission' and wt['permission'] in delegated_perms

    def show_for(wt: Dict[str, Any]) -> bool:
        if scope == 'my':
            if is_super:
                return wt['scope'] == 'super_admin_only' or (wt['scope'] == 'permission' and (not is_delegated(wt)))
            return wt['scope'] == 'permission' and wt['permission'] in real_perms
        return is_delegated(wt) and (is_super or wt['permission'] not in real_perms)
    rank = {'critical': 0, 'high': 1, 'normal': 2, 'low': 3}
    items = []
    for wt in WORK_TYPES:
        key = wt['key']
        if not show_for(wt):
            continue
        opens = await db.work_items.find({'work_type': key, 'status': 'open'}, {'_id': 0, 'opened_at': 1}).to_list(20000)
        sla = int(settings['sla_days'].get(key, wt['sla_days_default']))
        overdue = sum((1 for o in opens if _is_overdue(o.get('opened_at'), sla)))
        oldest = min((o.get('opened_at') for o in opens if o.get('opened_at')), default=None)
        items.append({'work_type': key, 'label_id': wt['label_id'], 'label_en': wt['label_en'], 'icon': wt['icon'], 'link': wt['link'], 'permission': wt['permission'], 'priority': wt['priority'], 'scope': wt['scope'], 'delegated': is_delegated(wt), 'open_count': len(opens), 'overdue_count': overdue, 'oldest_open_at': oldest, 'oldest_age_days': _age_days(oldest) if oldest else 0, 'sla_days': sla, 'can_act': True if is_super else wt['scope'] == 'permission' and wt['permission'] in real_perms})
    items.sort(key=lambda d: (0 if d['overdue_count'] else 1, rank.get(d['priority'], 9), d.get('oldest_open_at') or '9999'))
    return {'scope': scope, 'items': items, 'is_manager': bool(is_manage or is_super)}
