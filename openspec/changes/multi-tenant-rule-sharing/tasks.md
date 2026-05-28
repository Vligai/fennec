## 1. Org Rule API (Server-Side)

- [ ] 1.1 Add `org_rules` table to the hosted service DB (org_id, rule_id, type, pattern, taint_type, scope_glob, mode, created_by, created_at)
- [ ] 1.2 Implement `GET /api/v1/org/{org_id}/rules` endpoint — returns JSON array, requires valid API key
- [ ] 1.3 Implement `POST /api/v1/org/{org_id}/rules` endpoint — org admin only, validates pattern field is non-empty
- [ ] 1.4 Implement 403 response for non-admin publish attempts
- [ ] 1.5 Write API tests: admin can publish, non-admin rejected, fetch returns correct rules for org

## 2. Org Rule Fetch and Cache (Client-Side)

- [ ] 2.1 Implement `OrgRuleClient.fetch(org_id, api_key) -> List[OrgRule]` with 5-minute local cache
- [ ] 2.2 Implement cache fallback: on network error, use cached rules and log warning; on cache miss, return empty list with warning
- [ ] 2.3 Write unit tests: cache hit skips API call; cache miss fetches; API error uses stale cache

## 3. Rule Merge Logic

- [ ] 3.1 Extend `CustomRules` loader to accept `org_rules: List[OrgRule]` parameter
- [ ] 3.2 Implement merge: combine org + repo rules; repo rules win on same-pattern conflict
- [ ] 3.3 Implement `action: disable` override processing: remove matching org rules from effective set
- [ ] 3.4 Implement debug-mode logging of effective rule set with source annotation
- [ ] 3.5 Write unit tests: repo rule overrides org; disable removes org rule; non-conflicting rules combined

## 4. CLI Integration

- [ ] 4.1 Implement `fennec rules publish --org --pattern "<pattern>" --type sanitizer --vuln-class cmdi` CLI command
- [ ] 4.2 Validate pattern exists in graph before allowing org publish (same check as AI suggest)
- [ ] 4.3 Wire `FENNEC_ORG_ID` env var into scan startup: fetch org rules if set, skip if not set
- [ ] 4.4 Write integration test: end-to-end publish + scan flow with org rule applied
