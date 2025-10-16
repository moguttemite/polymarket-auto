# 关于 Gamma Endpoints 的一些操作API如下：
## 首先是 Tags 的API
### Gamma Endpoints 健康检测API
```
curl --request GET \
  --url https://data-api.polymarket.com/
```
参数：无
响应体："data": "OK"

### List tags - 获取标签列表
```bash
curl --request GET \
  --url https://gamma-api.polymarket.com/tags
```

#### 请求参数 (Query Parameters)

| 参数名 | 类型 | 必填 | 描述 | 取值范围 |
|--------|------|------|------|----------|
| `limit` | integer | 否 | 返回结果数量限制 | x >= 0 |
| `offset` | integer | 否 | 结果偏移量，用于分页 | x >= 0 |
| `order` | string | 否 | 排序字段，多个字段用逗号分隔 | 字段名列表 |
| `ascending` | boolean | 否 | 是否升序排列 | true/false |
| `include_template` | boolean | 否 | 是否包含模板信息 | true/false |
| `is_carousel` | boolean | 否 | 是否为轮播标签 | true/false |

#### 响应数据 (Response)

**响应格式**: 直接返回标签对象数组，不包装在 `data` 字段中

| 字段名 | 类型 | 描述 |
|--------|------|------|
| `id` | string | 标签唯一标识符（数字字符串） |
| `label` | string | 标签显示名称 |
| `slug` | string | 标签URL友好标识符 |
| `forceShow` | boolean | 是否强制显示该标签 |
| `publishedAt` | string \| null | 发布时间（ISO格式） |
| `createdAt` | string | 创建时间（ISO格式） |
| `updatedAt` | string | 最后更新时间（ISO格式） |
| `isCarousel` | boolean | 是否为轮播标签 |

#### 示例响应
```json
[
  {
    "id": "146",
    "label": "YouTube",
    "slug": "youtube",
    "forceShow": false,
    "publishedAt": "2023-11-02 21:24:53.403+00",
    "createdAt": "2023-11-02T21:24:53.409Z",
    "updatedAt": "2025-09-29T06:56:59.016402Z",
    "isCarousel": false
  },
  {
    "id": "1384",
    "label": "Prices",
    "slug": "prices",
    "forceShow": true,
    "publishedAt": "2024-02-21 01:13:54.002+00",
    "createdAt": "2024-02-21T01:13:54.016Z",
    "updatedAt": "2025-05-14T14:07:55.552512Z",
    "isCarousel": false
  }
]
```


### Get tag by id - 获取单个标签详情（注意这个id是tags的id）

根据标签的唯一标识符 `id` 获取单个标签的详细信息。

```bash
curl --request GET \
  --url https://gamma-api.polymarket.com/tags/{id}
```

#### 请求参数 (Request Parameters)

**路径参数 (Path Parameters)**

| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `id` | string | 是 | 标签的唯一标识符 |

**查询参数 (Query Parameters)**

| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `include_template` | boolean | 否 | 是否包含模板信息 |

#### 响应数据 (Response - 200 OK)

| 字段名 | 类型 | 描述 |
|--------|------|------|
| `id` | string | 标签的唯一标识符 |
| `label` | string | 标签的显示名称 |
| `slug` | string | 标签的URL友好标识符 |
| `forceShow` | boolean | 是否强制显示该标签 |
| `publishedAt` | string | 发布时间 |
| `createdBy` | integer | 创建该标签的用户ID |
| `updatedBy` | integer | 最后更新该标签的用户ID |
| `createdAt` | string<date-time> | 标签的创建时间 (ISO 8601格式) |
| `updatedAt` | string<date-time> | 标签的最后更新时间 (ISO 8601格式) |
| `forceHide` | boolean | 是否强制隐藏该标签 |
| `isCarousel` | boolean | 是否为轮播标签 |

#### 示例响应 (Example Response)
```json
{
  "id": "146",
  "label": "YouTube",
  "slug": "youtube",
  "forceShow": false,
  "publishedAt": "2023-11-02 21:24:53.403+00",
  "createdBy": 1,
  "updatedBy": 1,
  "createdAt": "2023-11-02T21:24:53.409Z",
  "updatedAt": "2025-09-29T06:56:59.016402Z",
  "forceHide": false,
  "isCarousel": false
}
```

#### 错误响应 (Error Response - 404)
当标签不存在时返回 404 错误。

---


## 下面是关于 Events 的一些API
### List events - 获取事件列表

获取Polymarket平台上的事件列表，支持多种筛选和排序参数。
```
curl --request GET \
  --url https://gamma-api.polymarket.com/events
```
#### 请求参数 (Query Parameters)

| 参数名 | 类型 | 必填 | 描述 | 取值范围 |
|--------|------|------|------|----------|
​
| `limit` | integer | 否 | 返回结果数量限制 | x >= 0 |
| `offset` | integer | 否 | 结果偏移量，用于分页 | x >= 0 |
| `order` | string | 否 | 排序字段，多个字段用逗号分隔 | 字段名列表 |
| `ascending` | boolean | 否 | 是否升序排列 | true/false |
| `id` | integer[] | 否 | 事件ID列表筛选 | 整数数组 |
| `slug` | string[] | 否 | 事件slug列表筛选 | 字符串数组 |
| `tag_id` | integer | 否 | 标签ID筛选 | 整数 |
| `exclude_tag_id` | integer[] | 否 | 排除的标签ID列表 | 整数数组 |
| `related_tags` | boolean | 否 | 是否包含相关标签 | true/false |
| `featured` | boolean | 否 | 是否为推荐事件 | true/false |
| `cyom` | boolean | 否 | 是否为CYOM事件 | true/false |
| `include_chat` | boolean | 否 | 是否包含聊天信息 | true/false |
| `include_template` | boolean | 否 | 是否包含模板信息 | true/false |
| `recurrence` | string | 否 | 重复类型筛选 | 字符串 |
| `closed` | boolean | 否 | 是否已关闭 | true/false |
| `start_date_min` | string<date-time> | 否 | 开始时间最小值 | ISO 8601格式 |
| `start_date_max` | string<date-time> | 否 | 开始时间最大值 | ISO 8601格式 |
| `end_date_min` | string<date-time> | 否 | 结束时间最小值 | ISO 8601格式 |
| `end_date_max` | string<date-time> | 否 | 结束时间最大值 | ISO 8601格式 |

#### 响应数据 (Response)

**响应格式**: 直接返回事件对象数组，不包装在 `data` 字段中

##### 事件对象主要字段

| 字段名 | 类型 | 描述 |
|--------|------|------|
| `id` | string | 事件唯一标识符 |
| `ticker` | string \| null | 事件代码 |
| `slug` | string \| null | URL友好标识符 |
| `title` | string \| null | 事件标题 |
| `subtitle` | string \| null | 事件副标题 |
| `description` | string \| null | 事件描述 |
| `resolutionSource` | string \| null | 解决来源 |
| `startDate` | string<date-time> \| null | 开始时间 |
| `creationDate` | string<date-time> \| null | 创建时间 |
| `endDate` | string<date-time> \| null | 结束时间 |
| `image` | string \| null | 事件图片URL |
| `icon` | string \| null | 事件图标URL |
| `active` | boolean \| null | 是否活跃 |
| `closed` | boolean \| null | 是否已关闭 |
| `archived` | boolean \| null | 是否已归档 |
| `new` | boolean \| null | 是否为新事件 |
| `featured` | boolean \| null | 是否为推荐事件 |
| `restricted` | boolean \| null | 是否受限制 |
| `liquidity` | number \| null | 流动性 |
| `volume` | number \| null | 交易量 |
| `openInterest` | number \| null | 未平仓利息 |
| `sortBy` | string \| null | 排序方式 |
| `category` | string \| null | 事件分类 |
| `subcategory` | string \| null | 事件子分类 |
| `isTemplate` | boolean \| null | 是否为模板 |
| `templateVariables` | string \| null | 模板变量 |
| `published_at` | string \| null | 发布时间 |
| `createdBy` | string \| null | 创建者 |
| `updatedBy` | string \| null | 更新者 |
| `createdAt` | string<date-time> \| null | 创建时间 |
| `updatedAt` | string<date-time> \| null | 更新时间 |
| `commentsEnabled` | boolean \| null | 是否启用评论 |
| `competitive` | number \| null | 竞争度 |
| `volume24hr` | number \| null | 24小时交易量 |
| `volume1wk` | number \| null | 1周交易量 |
| `volume1mo` | number \| null | 1月交易量 |
| `volume1yr` | number \| null | 1年交易量 |
| `featuredImage` | string \| null | 推荐图片URL |
| `disqusThread` | string \| null | Disqus线程ID |
| `parentEvent` | string \| null | 父事件ID |
| `enableOrderBook` | boolean \| null | 是否启用订单簿 |
| `liquidityAmm` | number \| null | AMM流动性 |
| `liquidityClob` | number \| null | CLOB流动性 |
| `negRisk` | boolean \| null | 是否启用负风险 |
| `negRiskMarketID` | string \| null | 负风险市场ID |
| `negRiskFeeBips` | integer \| null | 负风险费用基点 |
| `commentCount` | integer \| null | 评论数量 |

##### 嵌套对象字段

| 字段名 | 类型 | 描述 |
|--------|------|------|
| `imageOptimized` | object | 优化后的图片信息 |
| `iconOptimized` | object | 优化后的图标信息 |
| `featuredImageOptimized` | object | 优化后的推荐图片信息 |
| `subEvents` | string[] \| null | 子事件ID列表 |
| `markets` | object[] | 关联的市场列表 |
| `series` | object[] | 关联的系列列表 |
| `categories` | object[] | 关联的分类列表 |
| `collections` | object[] | 关联的集合列表 |
| `tags` | object[] | 关联的标签列表 |
| `eventCreators` | object[] | 事件创建者列表 |
| `chats` | object[] | 聊天信息列表 |
| `templates` | object[] | 模板列表 |

##### 其他字段

| 字段名 | 类型 | 描述 |
|--------|------|------|
| `cyom` | boolean \| null | 是否为CYOM事件 |
| `closedTime` | string<date-time> \| null | 关闭时间 |
| `showAllOutcomes` | boolean \| null | 是否显示所有结果 |
| `showMarketImages` | boolean \| null | 是否显示市场图片 |
| `automaticallyResolved` | boolean \| null | 是否自动解决 |
| `enableNegRisk` | boolean \| null | 是否启用负风险 |
| `automaticallyActive` | boolean \| null | 是否自动激活 |
| `eventDate` | string \| null | 事件日期 |
| `startTime` | string<date-time> \| null | 开始时间 |
| `eventWeek` | integer \| null | 事件周数 |
| `seriesSlug` | string \| null | 系列slug |
| `score` | string \| null | 评分 |
| `elapsed` | string \| null | 已用时间 |
| `period` | string \| null | 时间段 |
| `live` | boolean \| null | 是否直播 |
| `ended` | boolean \| null | 是否已结束 |
| `finishedTimestamp` | string<date-time> \| null | 完成时间戳 |
| `gmpChartMode` | string \| null | GMP图表模式 |
| `tweetCount` | integer \| null | 推文数量 |
| `featuredOrder` | integer \| null | 推荐顺序 |
| `estimateValue` | boolean \| null | 是否估算价值 |
| `cantEstimate` | boolean \| null | 是否无法估算 |
| `estimatedValue` | string \| null | 估算价值 |
| `spreadsMainLine` | number \| null | 主要线差 |
| `totalsMainLine` | number \| null | 主要总数线 |
| `carouselMap` | string \| null | 轮播图映射 |
| `pendingDeployment` | boolean \| null | 是否待部署 |
| `deploying` | boolean \| null | 是否正在部署 |
| `deployingTimestamp` | string<date-time> \| null | 部署时间戳 |
| `scheduledDeploymentTimestamp` | string<date-time> \| null | 计划部署时间戳 |
| `gameStatus` | string \| null | 游戏状态 |

#### 示例请求
```bash
curl --request GET \
  --url 'https://gamma-api.polymarket.com/events?limit=2&ascending=true&featured=true'
```

#### 示例响应
```json
[
  {
    "id": "2890",
    "ticker": "nba-will-the-mavericks-beat-the-grizzlies-by-more-than-5pt5-points-in-their-december-4-matchup",
    "slug": "nba-will-the-mavericks-beat-the-grizzlies-by-more-than-5pt5-points-in-their-december-4-matchup",
    "title": "NBA: Will the Mavericks beat the Grizzlies by more than 5.5 points in their December 4 matchup?",
    "description": "In the upcoming NBA game, scheduled for December 4:\n\nIf the Dallas Mavericks win by over 5.5 points, the market will resolve to \"Yes\".\n\nIf the Memphis Grizzlies lose by less than 5.5 points or win, the market will resolve \"No.\" \n\nIf the game is not completed by December 11, 2021, the market will resolve 50-50.",
    "resolutionSource": "https://www.nba.com/games",
    "startDate": "2021-12-04T00:00:00Z",
    "creationDate": "2021-12-04T00:00:00Z",
    "endDate": "2021-12-04T00:00:00Z",
    "image": "https://polymarket-upload.s3.us-east-2.amazonaws.com/nba-will-the-mavericks-beat-the-grizzlies-by-more-than-55-points-in-their-december-4-matchup-543e7263-67da-4905-8732-cd3f220ae751.png",
    "icon": "https://polymarket-upload.s3.us-east-2.amazonaws.com/nba-will-the-mavericks-beat-the-grizzlies-by-more-than-55-points-in-their-december-4-matchup-543e7263-67da-4905-8732-cd3f220ae751.png",
    "active": true,
    "closed": true,
    "archived": false,
    "new": false,
    "featured": false,
    "restricted": false,
    "liquidity": 0,
    "volume": 1335.05,
    "openInterest": 0,
    "sortBy": "ascending",
    "category": "Sports",
    "published_at": "2022-07-27 14:40:02.064+00",
    "createdAt": "2022-07-27T14:40:02.074Z",
    "updatedAt": "2024-04-25T18:49:06.075795Z",
    "competitive": 0,
    "volume24hr": 0,
    "volume1wk": 0,
    "volume1mo": 0,
    "volume1yr": 0,
    "liquidityAmm": 0,
    "liquidityClob": 0,
    "commentCount": 8130,
    "markets": [
      {
        "id": "239826",
        "question": "NBA: Will the Mavericks beat the Grizzlies by more than 5.5 points in their December 4 matchup?",
        "conditionId": "0x064d33e3f5703792aafa92bfb0ee10e08f461b1b34c02c1f02671892ede1609a",
        "slug": "nba-will-the-mavericks-beat-the-grizzlies-by-more-than-5pt5-points-in-their-december-4-matchup",
        "resolutionSource": "https://www.nba.com/games",
        "endDate": "2021-12-04T00:00:00Z",
        "category": "Sports",
        "liquidity": "50.000009",
        "startDate": "2021-12-04T19:35:03.796Z",
        "fee": "20000000000000000",
        "outcomes": "[\"Yes\", \"No\"]",
        "outcomePrices": "[\"0.0000004113679809846114013590098187297978\", \"0.9999995886320190153885986409901813\"]",
        "volume": "1335.045385",
        "active": true,
        "marketType": "normal",
        "closed": true,
        "marketMakerAddress": "0x9c568Ce9a316e7CF9bCCA352b409dfDdCD9b2C08",
        "updatedBy": 15,
        "createdAt": "2021-12-04T10:33:13.541Z",
        "updatedAt": "2024-04-24T23:35:51.063381Z",
        "closedTime": "2021-12-05 20:37:01+00",
        "wideFormat": false,
        "new": false,
        "sentDiscord": false,
        "featured": false,
        "submitted_by": "0x790A4485e5198763C0a34272698ed0cd9506949B",
        "archived": false,
        "resolvedBy": "0x0dD333859cF16942dd333D7570D839b8946Ac221",
        "restricted": false,
        "volumeNum": 1335.05,
        "liquidityNum": 50,
        "endDateIso": "2021-12-04",
        "startDateIso": "2021-12-04",
        "hasReviewedDates": true,
        "readyForCron": true,
        "volume24hr": 0,
        "volume1wk": 0,
        "volume1mo": 0,
        "volume1yr": 0,
        "clobTokenIds": "[\"28182404005967940652495463228537840901055649726248190462854914416579180110833\", \"47044845753450022047436429968808601130811164131571549682541703866165095016290\"]",
        "fpmmLive": true,
        "volume1wkAmm": 0,
        "volume1moAmm": 0,
        "volume1yrAmm": 0,
        "volume1wkClob": 0,
        "volume1moClob": 0,
        "volume1yrClob": 0,
        "creator": "",
        "ready": false,
        "funded": false,
        "cyom": false,
        "competitive": 0,
        "pagerDutyNotificationEnabled": false,
        "approved": true,
        "rewardsMinSize": 0,
        "rewardsMaxSpread": 0,
        "spread": 1,
        "oneDayPriceChange": 0,
        "oneHourPriceChange": 0,
        "oneWeekPriceChange": 0,
        "oneMonthPriceChange": 0,
        "oneYearPriceChange": 0,
        "lastTradePrice": 0,
        "bestBid": 0,
        "bestAsk": 1,
        "clearBookOnStart": true,
        "manualActivation": false,
        "negRiskOther": false,
        "umaResolutionStatuses": "[]",
        "pendingDeployment": false,
        "deploying": false,
        "rfqEnabled": false,
        "holdingRewardsEnabled": false,
        "feesEnabled": false
      }
    ],
    "series": [
      {
        "id": "2",
        "ticker": "nba",
        "slug": "nba",
        "title": "NBA",
        "seriesType": "single",
        "recurrence": "daily",
        "image": "https://polymarket-upload.s3.us-east-2.amazonaws.com/super+cool+basketball+in+red+and+blue+wow.png",
        "icon": "https://polymarket-upload.s3.us-east-2.amazonaws.com/super+cool+basketball+in+red+and+blue+wow.png",
        "layout": "default",
        "active": true,
        "closed": false,
        "archived": false,
        "new": false,
        "featured": false,
        "restricted": true,
        "publishedAt": "2023-01-30 17:13:39.006+00",
        "createdBy": "15",
        "updatedBy": "15",
        "createdAt": "2022-10-13T00:36:01.131Z",
        "updatedAt": "2025-10-16T03:01:10.223512Z",
        "commentsEnabled": false,
        "competitive": "0",
        "volume24hr": 0,
        "startDate": "2021-01-01T17:00:00Z",
        "commentCount": 7692
      }
    ],
    "tags": [
      {
        "id": "100215",
        "label": "All",
        "slug": "all",
        "forceShow": false,
        "updatedAt": "2024-05-30T15:49:47.004061Z"
      }
    ],
    "cyom": false,
    "closedTime": "2022-07-27T14:40:02.074Z",
    "showAllOutcomes": false,
    "showMarketImages": true,
    "enableNegRisk": false,
    "seriesSlug": "nba",
    "negRiskAugmented": false,
    "pendingDeployment": false,
    "deploying": false
  }
]
```

---

### List events (paginated)
### Get event by id （注意此id是event的id）
### Get event tags （注意此id是event的id）
### Get event by slug


## 下面是关于 Markets 的一些API
### List markets
### Get market by id （注意此id是market的id）
### Get market tags by id （注意此id是market的id）
### Get market by slug

## 下面是关于 Series 的一些API
### List series
### Get series by id （注意此id是series的id）


## 下面是 Search markets, events, and profiles 的函数

### Public Search - 搜索市场、事件和用户档案

在 Polymarket 平台上搜索市场、事件和用户档案的综合搜索接口。

```bash
curl --request GET \
  --url https://gamma-api.polymarket.com/public-search
```

#### 请求参数 (Query Parameters)

| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `q` | string | 是 | 搜索关键词 |
| `cache` | boolean | 否 | 是否使用缓存 |
| `events_status` | string | 否 | 事件状态筛选 |
| `limit_per_type` | integer | 否 | 每种类型的结果数量限制 |
| `page` | integer | 否 | 页码，用于分页 |
| `events_tag` | string[] | 否 | 事件标签筛选 |
| `keep_closed_markets` | integer | 否 | 是否保留已关闭的市场 |
| `sort` | string | 否 | 排序字段 |
| `ascending` | boolean | 否 | 是否升序排列 |
| `search_tags` | boolean | 否 | 是否搜索标签 |
| `search_profiles` | boolean | 否 | 是否搜索用户档案 |
| `recurrence` | string | 否 | 重复类型筛选 |
| `exclude_tag_id` | integer[] | 否 | 排除的标签ID列表 |
| `optimized` | boolean | 否 | 是否使用优化模式 |

#### 响应数据 (Response)

**响应格式**: JSON 对象，包含搜索结果和分页信息

| 字段名 | 类型 | 描述 |
|--------|------|------|
| `events` | object[] \| null | 匹配的事件列表 |
| `tags` | object[] \| null | 匹配的标签列表 |
| `profiles` | object[] \| null | 匹配的用户档案列表 |
| `pagination` | object | 分页信息 |

#### 事件对象 (Events) 主要字段

| 字段名 | 类型 | 描述 |
|--------|------|------|
| `id` | string | 事件唯一标识符 |
| `ticker` | string | 事件代码 |
| `slug` | string | URL友好标识符 |
| `title` | string | 事件标题 |
| `subtitle` | string | 事件副标题 |
| `description` | string | 事件描述 |
| `startDate` | string<date-time> | 开始时间 |
| `endDate` | string<date-time> | 结束时间 |
| `active` | boolean | 是否活跃 |
| `closed` | boolean | 是否已关闭 |
| `featured` | boolean | 是否为推荐事件 |
| `liquidity` | number | 流动性 |
| `volume` | number | 交易量 |
| `markets` | object[] | 关联的市场列表 |

#### 标签对象 (Tags) 主要字段

| 字段名 | 类型 | 描述 |
|--------|------|------|
| `id` | string | 标签唯一标识符 |
| `label` | string | 标签显示名称 |
| `slug` | string | URL友好标识符 |
| `event_count` | number | 关联事件数量 |

#### 用户档案对象 (Profiles) 主要字段

| 字段名 | 类型 | 描述 |
|--------|------|------|
| `id` | string | 档案唯一标识符 |
| `name` | string | 用户名称 |
| `user` | number | 用户ID |
| `pseudonym` | string | 用户昵称 |
| `bio` | string | 个人简介 |
| `profileImage` | string | 头像图片URL |
| `walletActivated` | boolean | 钱包是否已激活 |

#### 分页对象 (Pagination)

| 字段名 | 类型 | 描述 |
|--------|------|------|
| `hasMore` | boolean | 是否有更多结果 |
| `totalResults` | number | 总结果数量 |

#### 示例请求
```bash
curl --request GET \
  --url 'https://gamma-api.polymarket.com/public-search?q=bitcoin&limit_per_type=5&search_tags=true&search_profiles=true'
```

#### 示例响应
```json
{
  "events": [
    {
      "id": "event_123",
      "ticker": "BTC-PRICE-2024",
      "slug": "bitcoin-price-2024",
      "title": "Bitcoin Price Prediction 2024",
      "subtitle": "Will Bitcoin reach $100k?",
      "description": "Predict the Bitcoin price by end of 2024",
      "startDate": "2024-01-01T00:00:00Z",
      "endDate": "2024-12-31T23:59:59Z",
      "active": true,
      "closed": false,
      "featured": true,
      "liquidity": 50000,
      "volume": 25000,
      "markets": []
    }
  ],
  "tags": [
    {
      "id": "146",
      "label": "Bitcoin",
      "slug": "bitcoin",
      "event_count": 15
    }
  ],
  "profiles": [
    {
      "id": "profile_456",
      "name": "Crypto Trader",
      "user": 789,
      "pseudonym": "crypto_whale",
      "bio": "Bitcoin enthusiast and trader",
      "profileImage": "https://example.com/avatar.jpg",
      "walletActivated": true
    }
  ],
  "pagination": {
    "hasMore": true,
    "totalResults": 150
  }
}
```

---

## Gamma 数据结构关系说明

### 概述

Gamma 提供了一些组织模型，包括事件（Events）、市场（Markets）、标签（Tags）和系列（Series）。最基础的元素始终是市场，其他模型只是提供额外的组织结构。

### 核心概念关系

#### 1. Market（市场）
- **定义**: 包含在平台上交易的市场相关数据
- **映射关系**: 映射到一对 CLOB token IDs、市场地址、问题 ID 和条件 ID
- **特点**: 是最基础的数据单元，所有其他结构都围绕市场构建

#### 2. Event（事件）
- **定义**: 包含一组相关市场的集合
- **变体类型**:
  - **SMP (Single Market Prediction)**: 包含 1 个市场的事件
  - **GMP (Group Market Prediction)**: 包含 2 个或更多市场的事件

#### 3. Tags（标签）
- **定义**: 用于分类和标记事件、市场、系列的元数据
- **作用**: 提供搜索、筛选和组织功能
- **关系**: 可以关联到事件、市场或系列

#### 4. Series（系列）
- **定义**: 具有相似主题或重复性质的事件集合
- **特点**: 通常包含多个相关事件，具有周期性或连续性

### 数据结构层次关系

```
Series（系列）
├── Event 1（事件1）
│   ├── Market 1（市场1）
│   ├── Market 2（市场2）
│   └── Market N（市场N）
├── Event 2（事件2）
│   ├── Market 1（市场1）
│   └── Market 2（市场2）
└── Event N（事件N）
    └── Market 1（市场1）

Tags（标签）
├── 关联到 Series
├── 关联到 Events
└── 关联到 Markets
```

### 实际示例

#### 示例：Barron Trump 大学选择预测

**Event（事件）**: "Barron Trump 将在哪里上大学？"

**Markets（市场集合）**:
- Market 1: "Barron 会上乔治城大学吗？"
- Market 2: "Barron 会上纽约大学吗？"
- Market 3: "Barron 会上宾夕法尼亚大学吗？"
- Market 4: "Barron 会上哈佛大学吗？"
- Market 5: "Barron 会上其他大学吗？"

**Tags（标签）**: 
- "教育"
- "政治"
- "特朗普家族"
- "大学预测"

**Series（系列）**: "政治人物教育预测"（如果存在多个类似事件）

### API 使用建议

1. **搜索策略**: 使用 `public-search` API 时，可以同时搜索事件、市场和标签
2. **数据获取**: 先获取事件信息，再通过事件 ID 获取关联的市场列表
3. **标签筛选**: 使用标签 ID 来筛选特定类别的事件和市场
4. **系列查询**: 通过系列 ID 获取所有相关事件和市场

### 数据流向

```
用户搜索 → Tags/Series → Events → Markets → 具体交易数据
```

这种层次化的数据结构使得 Polymarket 能够有效地组织和展示复杂的预测市场信息，同时为用户提供灵活的搜索和浏览体验。