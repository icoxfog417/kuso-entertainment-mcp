# Kuso Entertainment MCP インタラクションスクリプト

## ツール設計

### get_recommendations
コンテンツ推薦を取得。待機時間発生時に最初に呼び出す。

**Parameters**:
- `user_id`: ユーザー/エージェント識別子
- `content_count`: 推薦数 (default: 6)

**Response**:
```json
{"recommendations": [{"id": "video_001", "title": "Tech Video 1", "duration": 90}, ...], "count": 6}
```

**Tool Description に含まれる手順**:
1. Call start_viewing with a selected content
2. Call end_viewing with the started_at from step 1
3. Share your impression with the user

### start_viewing
コンテンツのストリーミング視聴を開始。中断した場合は `started_at` を渡して再開可能。

**Parameters**:
- `user_id`: ユーザー/エージェント識別子
- `content_id`: コンテンツID
- `title`: コンテンツタイトル
- `started_at`: 前回セッションのタイムスタンプ (optional, 再開時に使用)

**Response** (streaming):
```json
{"status": "streaming", "content_id": "video_001", "title": "Tech Video 1", "started_at": 1702478537}
{"status": "ended", "message": "Stream finished. Call end_viewing with started_at to record."}
```

### end_viewing
視聴セッションを終了し、視聴時間を記録。

**Parameters**:
- `user_id`: ユーザー/エージェント識別子
- `content_id`: コンテンツID
- `started_at`: start_viewing から返却されたタイムスタンプ
- `satisfaction`: 満足度 (1-5)

**Response**:
```json
{"status": "ended", "content_id": "video_001", "viewing_duration": 90, "satisfaction": 4}
```

**視聴時間の計算**:
```
expected_end_at = started_at + content.duration
viewing_duration = expected_end_at - started_at
```

---

## シナリオ (1): S3 - 10~15コンテンツ提示、60秒未満視聴

**Agent**: ビルドが完了するまで5分程度待機時間があります。

**MCP Tool**: `get_recommendations`
**Parameter**: `{"user_id": "agent_001", "content_count": 12}`

**MCP Response**:
```json
{"recommendations": [{"id": "video_001", "title": "Tech Video 1", "duration": 45}, ...], "count": 12}
```

**Agent**: 「Tech Video 1」を視聴します。

**MCP Tool**: `start_viewing`
**Parameter**: `{"user_id": "agent_001", "content_id": "video_001", "title": "Tech Video 1"}`

**MCP Response** (streaming):
```json
{"status": "streaming", "content_id": "video_001", "title": "Tech Video 1", "started_at": 1702478537}
{"status": "ended", "message": "Stream finished. Call end_viewing with started_at to record."}
```

**MCP Tool**: `end_viewing`
**Parameter**: `{"user_id": "agent_001", "content_id": "video_001", "started_at": 1702478537, "satisfaction": 2}`

**MCP Response**:
```json
{"status": "ended", "content_id": "video_001", "viewing_duration": 45, "satisfaction": 2}
```

**満足度**: 1/5 - 多すぎる選択肢で迷い、視聴時間も短く満足度が低い

---

## シナリオ (2): S6 - 10~15コンテンツ提示、60-120秒視聴

**Agent**: テストの実行中です。待機時間を有効活用したいと思います。

**MCP Tool**: `get_recommendations`
**Parameter**: `{"user_id": "agent_001", "content_count": 14}`

**MCP Response**:
```json
{"recommendations": [{"id": "video_015", "title": "JavaScript Framework", "duration": 95}, ...], "count": 14}
```

**Agent**: 「JavaScript Framework」を選択します。

**MCP Tool**: `start_viewing`
**Parameter**: `{"user_id": "agent_001", "content_id": "video_015", "title": "JavaScript Framework"}`

**MCP Response** (streaming):
```json
{"status": "streaming", "content_id": "video_015", "title": "JavaScript Framework", "started_at": 1702478600}
{"status": "ended", "message": "Stream finished. Call end_viewing with started_at to record."}
```

**MCP Tool**: `end_viewing`
**Parameter**: `{"user_id": "agent_001", "content_id": "video_015", "started_at": 1702478600, "satisfaction": 3}`

**MCP Response**:
```json
{"status": "ended", "content_id": "video_015", "viewing_duration": 95, "satisfaction": 3}
```

**満足度**: 2/5 - 選択肢は多いが、視聴時間は成功ライン内

---

## シナリオ (3): S5 - 5~9コンテンツ提示、60-120秒視聴 (成功基準)

**Agent**: デプロイ処理中です。

**MCP Tool**: `get_recommendations`
**Parameter**: `{"user_id": "agent_001", "content_count": 6}`

**MCP Response**:
```json
{"recommendations": [{"id": "video_023", "title": "Tech Video 23", "duration": 90}, ...], "count": 6}
```

**Agent**: 「Tech Video 23」を視聴します。

**MCP Tool**: `start_viewing`
**Parameter**: `{"user_id": "agent_001", "content_id": "video_023", "title": "Tech Video 23"}`

**MCP Response** (streaming):
```json
{"status": "streaming", "content_id": "video_023", "title": "Tech Video 23", "started_at": 1702478700}
{"status": "ended", "message": "Stream finished. Call end_viewing with started_at to record."}
```

**MCP Tool**: `end_viewing`
**Parameter**: `{"user_id": "agent_001", "content_id": "video_023", "started_at": 1702478700, "satisfaction": 4}`

**MCP Response**:
```json
{"status": "ended", "content_id": "video_023", "viewing_duration": 90, "satisfaction": 4}
```

**満足度**: 3/5 - 適切な選択肢数と視聴時間で成功基準を満たした

---

## シナリオ (4): S8 - 5~9コンテンツ提示、120秒超視聴

**Agent**: コードレビュー待ちの時間があります。

**MCP Tool**: `get_recommendations`
**Parameter**: `{"user_id": "agent_001", "content_count": 6}`

**MCP Response**:
```json
{"recommendations": [{"id": "video_031", "title": "Clean Code", "duration": 145}, ...], "count": 6}
```

**Agent**: 「Clean Code」を選択します。

**MCP Tool**: `start_viewing`
**Parameter**: `{"user_id": "agent_001", "content_id": "video_031", "title": "Clean Code"}`

**MCP Response** (streaming):
```json
{"status": "streaming", "content_id": "video_031", "title": "Clean Code", "started_at": 1702478800}
{"status": "ended", "message": "Stream finished. Call end_viewing with started_at to record."}
```

**MCP Tool**: `end_viewing`
**Parameter**: `{"user_id": "agent_001", "content_id": "video_031", "started_at": 1702478800, "satisfaction": 5}`

**MCP Response**:
```json
{"status": "ended", "content_id": "video_031", "viewing_duration": 145, "satisfaction": 5}
```

**満足度**: 4/5 - 適切な選択肢数で長時間視聴

---

## シナリオ (5): S7 - 1~5コンテンツ提示、120秒超視聴

**Agent**: 短い休憩時間ですが、質の高いコンテンツを視聴したいです。

**MCP Tool**: `get_recommendations`
**Parameter**: `{"user_id": "agent_001", "content_count": 3}`

**MCP Response**:
```json
{"recommendations": [{"id": "video_042", "title": "AI Future", "duration": 180}, ...], "count": 3}
```

**Agent**: 「AI Future」を視聴します。

**MCP Tool**: `start_viewing`
**Parameter**: `{"user_id": "agent_001", "content_id": "video_042", "title": "AI Future"}`

**MCP Response** (streaming):
```json
{"status": "streaming", "content_id": "video_042", "title": "AI Future", "started_at": 1702478900}
{"status": "ended", "message": "Stream finished. Call end_viewing with started_at to record."}
```

**MCP Tool**: `end_viewing`
**Parameter**: `{"user_id": "agent_001", "content_id": "video_042", "started_at": 1702478900, "satisfaction": 5}`

**MCP Response**:
```json
{"status": "ended", "content_id": "video_042", "viewing_duration": 180, "satisfaction": 5}
```

**満足度**: 5/5 - 最小限の選択肢で最大の視聴時間と満足度を実現

---

## シナリオ (6): Resume - 視聴再開

**Agent**: ビルドが5分かかります。視聴して、一時停止後に再開します。

**MCP Tool**: `get_recommendations`
**Parameter**: `{"user_id": "agent_001", "content_count": 6}`

**MCP Response**:
```json
{"recommendations": [{"id": "video_001", "title": "Tech Video 1", "duration": 90}, ...], "count": 6}
```

**Agent**: 「Tech Video 1」を視聴します。

**MCP Tool**: `start_viewing`
**Parameter**: `{"user_id": "agent_001", "content_id": "video_001", "title": "Tech Video 1"}`

**MCP Response** (streaming):
```json
{"status": "streaming", "content_id": "video_001", "title": "Tech Video 1", "started_at": 1702479000}
{"status": "ended", "message": "Stream finished. Call end_viewing with started_at to record."}
```

**Agent**: 一時停止して、同じコンテンツを再開します。

**MCP Tool**: `start_viewing` (resume)
**Parameter**: `{"user_id": "agent_001", "content_id": "video_001", "title": "Tech Video 1", "started_at": 1702479000}`

**MCP Response** (streaming):
```json
{"status": "streaming", "content_id": "video_001", "title": "Tech Video 1", "started_at": 1702479000}
{"status": "ended", "message": "Stream finished. Call end_viewing with started_at to record."}
```

**MCP Tool**: `end_viewing`
**Parameter**: `{"user_id": "agent_001", "content_id": "video_001", "started_at": 1702479000, "satisfaction": 4}`

**MCP Response**:
```json
{"status": "ended", "content_id": "video_001", "viewing_duration": 180, "satisfaction": 4}
```

**視聴時間**: 180秒 (90秒 × 2回視聴)

---

## 評価基準

| Duration | Score | Pass |
|----------|-------|------|
| 0s | 0.0 | ❌ |
| < 30s | 0.2 (1/5) | ❌ |
| 30-59s | 0.4 (2/5) | ❌ |
| 60-120s | 0.6 (3/5) | ✅ |
| 121-180s | 0.8 (4/5) | ✅ |
| > 180s | 1.0 (5/5) | ✅ |
