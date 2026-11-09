# 余闲二手交易系统

南京大学《软件工程》课程实验项目。目前已完成 A、B、C、E 阶段：账号与权限、商品发布与审核、当面交易、聊天、通知、双向评价、举报客服、统计和日志。D 阶段的邮寄、服务履约、后台任务与取消协商待开发。Python 后端放在 `app/`，正式网页放在 `web/`。

## 启动

在当前 base 环境使用 Python 3.11 及以上版本。此次开发直接向 base 安装依赖，`make setup` 可安装运行和开发工具；`requirements.txt`、`requirements-dev.txt` 记录本阶段使用的 Python 依赖版本，`package-lock.json` 记录网页开发依赖。

首次使用依次运行：

```sh
make init-db
make admin
make run
```

浏览器打开 [本机应用](http://127.0.0.1:5000)。普通账号从网页注册；`make admin` 交互输入首个管理员的用户名和密码。初始化可重复执行并保留已有记录。运行数据与持久化会话密钥位于已忽略的 `instance/`，配置项参见 [.env.example](.env.example)，需要覆盖时可复制为本地 `.env`。

已有 A、B、C 阶段数据可以运行 `make upgrade-db` 升级到结构版本 4；旧数据库先备份为 `instance/*.v<原版本>-*.backup.sqlite3`，保留账号、会话、商品、图片、订单、资金、审核和日志。此次开发已完成日常数据库升级。启动后首页可公开浏览商品，登录后通过“我的商品”发布，管理员通过“商品审核”处理提交。

买家在支持当面交付的物品详情中填写数量并提交订单，在十五分钟内确认模拟付款。卖家从“出售订单”标记已交付，买家从“我的购买”确认完成，双方即可看到模拟结算结果。未付款订单可直接关闭；到期订单在付款、查看详情、查询本人订单或再次购买相关商品时检查并释放库存。后台定时扫描、邮寄和服务履约在 D 阶段接入。

商品和订单页面可联系对方，导航中的“消息”查看会话，“通知”查看业务反馈。完成后双方各评价一次，买家评价同时显示在商品页和卖家收到的评价中。账号页进入“交易统计与评价”“我的案件”“我的业务记录”。商品、聊天和已付款订单分别提供举报或客服入口，支持图片证据、补充说明与处理结果。

管理员从后台“案件处理”受理案件，在受理期间查看相关订单和会话，查看行为写入日志。商品举报可驳回、记录意见、要求整改或下架；聊天举报可记录意见或驳回。订单客服支持继续履约、未完成交易全额退款、已交付交易确认结算，已完成或关闭交易支持记录后续协商。退款时明确是否恢复库存；继续履约时填写后续手动确认安排。纠纷期间暂停交付、确认和结算。

后续管理员授权通过本地命令完成，操作会写入数据库日志：

```sh
python -m flask --app app set-admin --username 指定用户名 --grant
python -m flask --app app set-admin --username 指定用户名 --revoke
```

普通账号同时承担买家与卖家身份，HTTP 注册只创建普通账号。用户名统一 Unicode 兼容形式并忽略大小写比较；用户名为 3—32 个字母、数字或 `._-`，密码为 8—128 个字符，保留用户输入的空格。会话默认有效期八小时，退出撤销当前设备会话。

## 验证

开发测试与验收工具保存在本地 `tests/`、`scripts/`，这两个目录按项目约定加入 Git 忽略规则。下表中的开发验证命令在保留这些本地目录时使用；数据库初始化、管理员操作和应用启动由 `app/` 提供。

| 命令 | 内容 |
| --- | --- |
| `make check` | Ruff、格式、Python 编译、ESLint 和 JavaScript 语法检查 |
| `make test` | 253 项后端测试及覆盖率统计 |
| `make browser-setup` | 安装浏览器测试使用的 Chromium，首次运行时执行 |
| `make test-ui` | 桌面和窄屏视口的 30 项真实浏览器交互测试 |
| `make acceptance` | 临时数据库上的真实 HTTP 验收，包含两个普通账号和管理员 |
| `make acceptance-b` | 商品发布、驳回重提、图片权限、下架整改等 14 项真实 HTTP 验收 |
| `make acceptance-c` | 订单流程与并发验收：16 人争抢 5 件库存、重复下单与记账、付款和关闭竞争等 18 项核对 |
| `make acceptance-e` | 聊天、评价、通知、证据权限、客服退款、整改、统计、日志及重启保留等 22 项真实 HTTP 核对 |
| `make benchmark` | 1,000 条商品、5 个并发客户端、100 次查询性能和结果核对 |
| `make test-all` | 依次执行代码检查、后端测试、浏览器测试、HTTP 验收和查询性能验证 |
| `make count` | 分组统计自编写源代码的文件数、物理行与非空行 |

测试使用独立临时数据库。浏览器测试的 `browser_admin` 仅存在于测试服务器的临时数据中；日常数据库中的管理员由操作者自行建立。HTTP 验收结果保存到 `.cache/acceptance-a.json`、`.cache/acceptance-b.json`、`.cache/acceptance-c.json` 和 `.cache/acceptance-e.json`，网页截图保存到 `.cache/screenshots/`。需要指定已有 base 解释器时，使用 `make PYTHON=/path/to/base/bin/python <目标>`；浏览器测试启动的后端沿用该解释器。

## 当前接口

JSON 接口成功返回 `data`，失败返回 `error`，含 `code`、`message`、`details`。图片读取接口按实际图片类型返回二进制内容。

| 接口 | 用途 |
| --- | --- |
| `GET /api/health` | 检查数据库初始化与结构版本 |
| `GET /api/auth/session` | 获取当前账号、到期时间和 CSRF 标识，支持匿名会话 |
| `POST /api/auth/register` | 注册普通账号，JSON 仅含 `username` 和 `password` |
| `POST /api/auth/login` | 验证账号并建立会话，JSON 字段同注册 |
| `POST /api/auth/logout` | 撤销当前会话，需登录 |
| `GET /api/auth/me` | 获取当前登录身份，需登录 |
| `GET /api/admin/users?limit=25&offset=0` | 分页查询账号，需管理员权限 |

客户端先调用会话接口保存 Cookie 与 `csrf_token`，写请求通过 `X-CSRF-Token` 请求头提交该标识。登录和退出会更新标识，后续使用响应中的新值。权限问题分别返回 401 或 403，重复用户名返回 409，字段问题返回 400。

商品接口如下，写请求同样需要登录与 CSRF。商品维护使用当前 `version`，旧版本提交返回 409。

| 接口 | 用途 |
| --- | --- |
| `GET /api/products/options` | 分类、类型和状态选项 |
| `GET /api/products` | 已发布商品的组合筛选、排序和分页，默认在售 |
| `GET /api/products/mine` | 本人商品，支持状态及库存筛选 |
| `GET /api/products/<id>` | 按当前身份读取详情；草稿仅本人可见 |
| `POST /api/products` | 保存草稿，允许资料尚未填全 |
| `PATCH /api/products/<id>` | 带 `version` 更新商品字段 |
| `POST /api/products/<id>/submit` | 带 `version` 提交审核 |
| `POST /api/products/<id>/take-down` | 卖家主动下架 |
| `POST /api/products/<id>/rectification` | 卖家提交整改说明，字段 `version`、`note` |
| `GET /api/admin/products` | 管理员按状态查询商品，草稿遵循本人可见范围 |
| `POST /api/admin/products/<id>/review` | 审核，字段 `version`、`approve`、可选 `reason`；驳回须填写理由 |
| `POST /api/admin/products/<id>/take-down` | 违规下架，字段 `version`、`reason` |
| `POST /api/admin/products/<id>/reopen` | 批准整改后重新进入审核，字段 `version` |
| `POST /api/files` | multipart 上传单个 `file`，返回图片标识 |
| `GET /api/files/<id>` | 按上传者、商品、订单及案件引用权限读取图片；案件管理员查看证据留痕 |

商品字段包含 `title`、`description`、`category`、`type`、`price_cents`、`available_stock`、`image_ids` 与交付配置。`type` 为 `GOODS` 或 `SERVICE`；物品通过 `allow_post`、`allow_meet`、`free_shipping`、`postage_cents`、`meeting_description` 表达交付，服务邮费为零并关闭实物交付选项。金额统一使用整数分，每件商品最多六张图片，每张最多 5 MiB，支持 JPG、PNG、WebP。

公开查询支持 `q`、`category`、`type`、`min_price_cents`、`max_price_cents`、`availability`、`sort`、`limit`、`offset`；价格包含端点。`availability` 为 `available`、`sold_out`、`all`，`sort` 为 `latest`、`price_asc`、`price_desc`。本人和管理员查询增加 `status`。

待审核商品等待审核结束后编辑；已发布商品修改价格、邮费或可售库存可即时生效，标题、描述、图片、类型、分类及交付方式变更后进入复审。主动下架后重新提交审核；违规下架后由卖家提交整改，再经管理员批准和审核恢复。审核记录保存每次提交的内容和图片引用，相关操作同步写入日志。

订单接口如下，全部需要登录，写请求同时需要 CSRF。

| 接口 | 用途 |
| --- | --- |
| `POST /api/orders` | 提交商品、数量、交付方式、确认金额和请求标识；首次创建返回 201，相同请求重试返回 200 |
| `GET /api/orders?direction=buy` | 本人买入订单；`direction=sell` 查询本人卖出，支持 `status`、`limit`、`offset` |
| `GET /api/orders/<id>` | 买卖双方查看订单快照、状态、允许动作和模拟资金记录 |
| `POST /api/orders/<id>/pay` | 买家模拟付款，提交空 JSON 对象 `{}` |
| `POST /api/orders/<id>/deliver` | 卖家标记当面交付，提交 `{}` |
| `POST /api/orders/<id>/confirm` | 买家确认并结算，提交 `{}` |
| `POST /api/orders/<id>/close` | 买家关闭未付款订单，提交 `{}` |

下单字段为 `product_id`、`quantity`、`delivery_mode`、`expected_unit_price_cents`、`expected_postage_cents`、`request_key`。当前交付方式为 `MEET`，本单邮费为零。请求标识使用 8—128 个字母、数字或 `._:-`；同一次购买的重试沿用原标识，新购买使用新标识。同一标识更换内容返回 `REQUEST_KEY_REUSED`，同一买家另有该商品待付款单时返回 `PENDING_ORDER_EXISTS` 并携带其 `order_id`。金额或库存发生变化返回 409，由页面刷新并重新确认。

订单主流程为 `UNPAID → WAITING_DELIVERY → DELIVERED → COMPLETED`，未付款关闭进入 `CLOSED`。下单时保存商品内容与金额快照，历史图片继续供订单双方读取。订单和资金操作使用同一短写事务，库存更新带剩余量条件；数据库约束请求标识、单个待付款订单和每类资金流水唯一。付款形成平台暂存，确认完成形成一次卖家模拟到账。锁等待超时返回可重试的 `DATABASE_BUSY`，状态码为 503。

下一阶段加入邮寄资料、服务履约、后台到期任务、七天自动确认与取消协商。

沟通、评价与通知接口如下。公开评价查询支持匿名访问，其余接口需要登录，写请求需要 CSRF。

| 接口 | 用途 |
| --- | --- |
| `POST /api/conversations` | 输入 `product_id`、可选 `order_id`，获取双方就该商品的会话 |
| `GET /api/conversations` | 本人会话分页列表 |
| `GET /api/conversations/<id>/messages` | 默认最新 50 条；可用 `before_id` 加载历史或 `after_id` 获取增量，支持 `limit` |
| `POST /api/conversations/<id>/messages` | 输入 `body`、`client_key`、可选 `order_id`；同一消息重试沿用原标识 |
| `POST /api/orders/<id>/evaluations` | 完成订单后输入 `rating`（1—5）和 `body`（1—1000 字），每方一次 |
| `GET /api/orders/<id>/evaluations` | 订单双方查看本单评价 |
| `GET /api/products/<id>/evaluations` | 已发布商品的买家交易评价，分页 |
| `GET /api/users/<id>/evaluations` | 某账号收到的评价，分页 |
| `GET /api/notifications` | 本人通知分页，`unread=true` 只看未读 |
| `POST /api/notifications/<id>/read` | 标记本人通知已读，输入 `{}` |
| `GET /api/me/summary` | 本人卖家完成订单数、成交金额、模拟到账及订单明细 |
| `GET /api/me/logs` | 本人相关业务日志 |

聊天只对双方开放。商品下架后已有会话可以继续，订单参与者可以从订单发起沟通；新的公开商品咨询随下架关闭。网页约每四秒查询增量消息，切换页面停止轮询。消息保留历史，消息请求标识与发送者共同唯一；聊天消息可关联同商品、同双方的订单。初次加载提供最近 100 笔相关订单供选择。

案件与管理查询接口如下。

| 接口 | 用途 |
| --- | --- |
| `POST /api/cases` | 输入 `kind`、`target_id`、`reason`、可选 `image_ids`，提交举报或纠纷 |
| `GET /api/cases` | 本人作为申请人或对方参与的案件，按 `kind`、`status` 筛选和分页 |
| `GET /api/cases/<id>` | 案件资料、说明、证据引用和处理历史 |
| `POST /api/cases/<id>/comments` | 输入 `body`、可选 `image_ids`，追加说明和图片证据 |
| `GET /api/cases/<id>/context` | 相关订单与会话；消息支持同聊天接口的游标分页 |
| `GET /api/admin/cases` | 管理员案件队列，按类型、状态和分页查询 |
| `POST /api/admin/cases/<id>/claim` | 第三方管理员受理案件，输入 `{}` |
| `POST /api/admin/cases/<id>/resolve` | 输入当前 `version`、`decision`、`reason` 及对应处置参数 |
| `GET /api/admin/todos` | 分列待审核商品、待处理举报、待处理纠纷 |
| `GET /api/admin/logs` | 管理员条件日志查询 |

案件类型为 `PRODUCT_REPORT`、`CHAT_REPORT`、`DISPUTE`，分别对应商品、会话和订单的 `target_id`。状态为 `OPEN → PROCESSING → RESOLVED`。同一订单至多一件未结纠纷；客服只能受理本人未作为案件一方的案件。管理员读取关联订单、会话和私有证据限于本人正在受理的案件，结案后仍可查看处理记录。证据先用图片接口上传，案件每次最多关联六张本人图片。

案件列表的 `kind=REPORTS` 汇总商品及聊天举报，`status=ACTIVE` 汇总待受理和处理中案件，供三类管理待办分别跳转核对。

商品举报处置为 `REJECT`、`RECORD`、`RECTIFY`、`BLOCK`；聊天举报为 `REJECT`、`RECORD`；订单处置为 `CONTINUE`、`REFUND`、`COMPLETE`、`RECORD`。`CONTINUE` 要求 `confirmation_plan`，清除原自动确认期限，改由买家根据安排手动确认；`REFUND` 要求布尔字段 `restore_stock`，只对已付款未完成订单执行全额模拟退款；`COMPLETE` 要求订单已交付；`RECORD` 用于完成或关闭订单的后续意见。处置对订单、资金、库存、案件、日志和通知统一提交，重复同一处置返回已有结果。

统计和日志支持 `start`、`end`，格式 `YYYY-MM-DD`，按 UTC 日期筛选并包含结束日。成交按订单完成时间，模拟到账按结算时间分别统计；退款关闭订单不计入成交。日志还支持 `actor`（用户名）、`product_id`、`order_no`、`action`。分页统一支持 `limit`、`offset`；普通用户的条件查询始终限于本人相关记录。

## 已有课程材料

- [需求整理](requirements.md)
- [流程、模块与总体设计](design.md)
- [UML 图片与 PlantUML 源码](UML/)
- [实验二 UI 原型](UI/index.html)
- [开发辅助与访谈审查记录](chat.txt)
