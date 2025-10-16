py_package/py-clob-client/examples 文件夹下是Polymarket官方包所提供的实例，在阅览相关资料和py-clob-client包实现的基础上，给这些实例加上详尽的注释。

目前 src/get_markets.py 中已经实现了获取当前最新的 limit 条市场预测数据的获取函数 fetch_recent_markets，返回的参数中包含


接下来我们来实现过去最新events的函数，将对应的函数实现在 src/get_events.py中，文件中已经有了curl的调用案例，并且相关的api和参数可以参考官方文档https://docs.polymarket.com/api-reference/events/list-events，参数要求
输入
    limit: number，返回最新的limit个event
    tags: []，只有包含列表中的tag的event才会被返回

返回结构（EventSummary）

每个 event 返回这些键即可：

id（string）——后续通过 eventId 再去拉 markets 的主键。


slug（string）——前端直达以及按 slug 精确拉取单个 event/market 的最佳实践。


title（string）——人读友好，列表展示用。


active（bool）、closed（bool）——是否仍在进行；一般我们默认只要 closed=false 的。


createdAt、startDate、endDate（ISO8601）——时间排序与到期管理。


liquidity、volume、openInterest（number）——用来粗排“值得看”的事件。


enableOrderBook（bool）——该 event 下的市场是否可走 CLOB（撮合下单）。


tags（Array<{ id, slug, label }>）——把官方返回的 tag 对象拍扁，仅保留这三项，便于前端展示与二次过滤。


marketsCount（number|null）——若响应里自带 markets 数组就取其长度，否则置 null（等下游再查）。


url（string）——拼成 https://polymarket.com/event/{slug} 的直达链接（便于人工复核）。

说明：下单仍需到 Market 级别拿 clobTokenIds 等参数，EventSummary 刻意“轻量”，把重信息留给 get_markets_for_event(eventId)。市场级字段详见 Markets 文档（含 clobTokenIds、acceptingOrders 等）。



下面我们来实现 src/select_event.py 文件，功能是选出值得get_event中最值得下单的那个event，按着以下方案施行：



