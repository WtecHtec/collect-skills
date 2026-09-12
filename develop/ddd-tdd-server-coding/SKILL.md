---
name: ddd-tdd-server-coding
description: "Use this skill whenever writing or reviewing server-side business logic code, designing a new backend module/service, or refactoring existing server code. Triggers include: requests to implement a feature/API/use case on the backend, requests to design a service's directory/package structure, requests to decide where a piece of logic belongs (business rule vs technical detail), any mention of DDD / domain-driven design / interface-application-domain-infrastructure layering, and any request to write server code 'with tests first' / TDD. Also use when the user asks to review whether a layering boundary was violated, whether an implementation missed edge cases, or wants a deterministic acceptance checklist / test case record for a backend change. Do NOT use for frontend/UI code, pure scripts/data-analysis tasks, or infra-as-code (Terraform/K8s manifests) unrelated to application business logic."
---

# 服务端 DDD 四层架构 + TDD 编码规范

## 何时使用本 Skill

- 需要实现一个后端业务功能 / API / 用例。
- 需要设计一个新模块或新服务的目录结构。
- 需要判断"这段逻辑该放哪一层"（业务规则 vs 技术细节）。
- 需要按 TDD（先测试后实现）方式写服务端代码。
- 需要检查已有实现是否违反分层边界、是否遗漏异常边界/隐含约束。
- 需要为一次后端改动整理确定性的验收标准和测试用例记录。

不适用于：前端/UI 代码、与业务逻辑无关的纯脚本/数据分析任务、基础设施即代码（Terraform/K8s 编排本身，而非应用业务逻辑）。

---

## 一、四层架构定义

```
interface        (对外壳)      —— 协议适配，不含业务逻辑
    ↓ 依赖
application      (编排层)      —— 用例编排、事务边界，不含业务规则
    ↓ 依赖              ↓ 依赖
domain (核心层)     infrastructure (脏活层)
实体/值对象/           仓储实现/三方SDK/
领域服务/仓储接口       MQ/缓存/网络IO 等
(抽象)，零外部依赖      技术细节
    ↑------------------实现
```

**依赖方向铁律**：
- `interface → application`
- `application → domain`（调用业务规则）**且** `application → infrastructure`（直接使用技术能力）——application 层允许同时依赖 domain 和 infrastructure，不必所有基础设施能力都强行包一层 domain 抽象。
- `infrastructure → domain`（实现 domain 定义的抽象接口，如仓储实现）
- domain 层永远不 import application / infrastructure / interface 任何符号，这条对 domain 依然是铁律不能破。违反视为架构缺陷，必须在 code review / 自查阶段拦截。

**application 何时走 domain 抽象、何时可以直接调 infrastructure：**

| 场景 | 应该怎么做 |
|---|---|
| 涉及业务实体的持久化（仓储）、代表业务概念的外部能力（如"通知网关""支付网关"） | application 依赖 domain 定义的抽象接口，运行时注入 infrastructure 的具体实现（依赖倒置，方便替换/测试 mock） |
| 纯技术性编排能力，不代表任何业务语言（事务管理器/Unit of Work、分布式锁、幂等去重组件、事件总线发布器、日志/链路追踪） | application 可以直接持有并调用 infrastructure 的具体实现，不需要在 domain 里为它专门定义抽象 |

判断标准：**这个能力有没有业务语义、未来是否可能因为业务原因（而非纯技术选型原因）被替换** —— 有业务语义 → 走 domain 抽象；纯技术编排 → application 直接调用 infrastructure 即可，避免为了"分层洁癖"过度抽象。

### 1. interface 层
- 职责：协议转换（HTTP/RPC/MQ消费入口/CLI），参数反序列化、DTO ↔ 命令对象转换，鉴权/限流等横切关注点的接入点。
- 边界：**不写任何业务判断**（例如"库存不足则拒绝"这类规则不能出现在 controller 里）。只做"外部世界的语言"到"内部命令"的翻译。
- 反馈信号：如果 interface 层出现 if/else 判断业务状态，说明业务逻辑泄漏，需打回 domain/application。

### 2. application 层
- 职责：编排一个用例（use case）需要哪些 domain 服务、哪些仓储，同时可以直接调用 infrastructure 提供的技术能力（事务、分布式锁、事件发布、幂等控制等），控制事务边界（一个 application service 方法 = 一个事务/一个用例）。
- 边界：**不写业务规则，只写编排顺序**。可以调用 infrastructure，但不能把 infrastructure 的技术细节（如 SQL 语句、三方接口的原始报文结构）泄漏到编排逻辑的判断条件里——判断"是否满足某业务条件"必须委托给 domain，application 只管"调用谁、以什么顺序调用、失败了怎么走"。
- 反馈信号：如果同一段编排逻辑在多个用例里重复出现且是"业务判断"，应该下沉到 domain；如果只是"调用顺序"重复，可以抽 application 内的私有方法。如果 application 里出现了对 infrastructure 返回结果做业务规则判断（例如根据查出来的库存数字决定是否允许下单），说明业务逻辑泄漏，应该把判断逻辑收回 domain。

### 3. domain 层
- 职责：实体（Entity）、值对象（VO）、聚合根、领域服务（Domain Service）、领域事件、仓储接口（抽象，不含实现）、业务异常定义。
- 边界：**零第三方依赖**（不 import DB driver、HTTP client、MQ SDK、日期时区库以外的三方库尽量避免）。domain 里的"仓储"只是接口。
- domain 是这套规范里最需要"守护"的一层：一旦被基础设施细节污染，未来替换实现（换数据库/换MQ/换三方支付）就要动核心业务代码。

### 4. infrastructure 层
- 职责：domain 定义的仓储接口的具体实现（MySQL/Redis/Mongo/ES）、三方服务 SDK 封装（支付、短信、对象存储）、消息队列的生产/消费适配、技术性异常到领域异常的转译。
- 定位：**"脏活"层**——凡是跟具体技术选型、外部系统强绑定、易变、不稳定的实现都放这里。

---

## 二、domain vs infrastructure 判断准则（按顺序判断，命中即止）

写一段代码前，按下面顺序问自己三个问题，决定它该放哪一层：

### 判断1：是否需要"可替换性"？
- 如果这个能力未来有被替换的可能（换存储、换三方支付、换消息中间件、换缓存），**必须**在 domain 定义抽象（interface/abstract class），在 infrastructure 写具体实现，通过依赖注入接入。
- 反例：直接在 domain service 里 `new RedisClient()` —— 违规，锁死实现。

### 判断2：是否依赖第三方能力？
- 需要第三方 SDK / 网络调用 / 数据库驱动 / 文件系统 / 系统时钟以外的外部依赖 → 放 **infrastructure**。
- 不需要任何外部依赖，纯内存计算/纯规则判断 → 可以放 **domain**。
- 判断1和判断2冲突时，判断1优先：即使暂时没有三方依赖，但预判未来大概率会引入第三方（如"发送通知"），也应先在 domain 定义抽象接口。

### 判断3：从业务稳定性判断
- 高频变动、强技术细节相关（限流阈值调整、缓存过期策略、SQL索引优化）→ **infrastructure** 具体实现里调，不侵入 domain。
- 低频变动、代表企业核心规则（"订单满100减20"、"会员等级计算规则"）→ **domain** 里写具体实现（这类不需要抽象，因为规则本身就是业务而非技术选型）。

> 一句话总结：**domain 决定"做什么"和"业务规则是什么"，infrastructure 负责"具体怎么做"这些脏活、易变、外部依赖重的事。**

### 快速自查表

| 特征 | 归属 |
|---|---|
| 定义"订单"实体及其状态迁移规则 | domain（具体实现） |
| 调用短信服务商 API 发验证码 | infrastructure（具体实现，domain 定义 `NotificationGateway` 抽象） |
| 计算折扣金额的业务公式 | domain（具体实现） |
| 从 MySQL 查询订单 | infrastructure 实现 `OrderRepository`（domain 定义接口） |
| 判断订单是否可取消 | domain（具体实现，纯规则判断） |
| 序列化对象存到 Redis | infrastructure |
| 幂等键生成策略（依赖分布式ID服务） | infrastructure 实现，domain 定义 `IdGenerator` 抽象 |

---

## 三、TDD 强制流程（Red → Green → Refactor）

每个功能点/每个方法级别的实现，必须遵循以下顺序，**不允许先写实现代码**：

### Step 1 — Red（红灯）
1. 先明确这段代码的验收标准（见第五节），转化为一条或多条测试用例。
2. 编写测试代码，**运行并确认失败**（且要确认失败原因是"功能未实现"，不是编译错误、typo、测试本身写错）。
3. 把失败的错误信息记录下来（哪怕只是终端输出），作为"确实是 red 状态"的证据。

### Step 2 — Green（绿灯）
1. 编写**最小可行实现**让测试通过，不做额外设计、不过度抽象。
2. 运行测试，确认全部通过。禁止跳过失败用例（no `.skip`/注释掉断言）。

### Step 3 — Refactor（重构）
1. 在测试保护下重构代码结构（消除重复、优化命名、抽象下沉/上提）。
2. 每次重构后重新跑一遍全部相关测试，确保仍是绿灯。
3. 重构不改变外部行为——如果发现需要改变行为，说明这是新需求，退回 Step 1。

### 各层测试策略

| 层 | 测试类型 | Mock 策略 |
|---|---|---|
| domain | 单元测试 | 几乎不 mock（domain 无外部依赖，天然可测） |
| application | 用例测试 | mock 掉 domain 仓储接口和 infrastructure 网关，验证编排顺序、事务边界 |
| infrastructure | 集成测试 | 真实依赖或 testcontainer/沙箱，验证与外部系统的契约 |
| interface | 契约测试 | mock application 层，验证协议转换、参数校验、状态码 |

---

## 四、边界与隐含约束自查清单

每次实现前后，必须显式过一遍以下清单，**发现问题及时反馈给需求方确认，不要自行假设**：

### 异常边界
- [ ] 非法输入（空值/超长/类型错误/越界）如何处理？在哪一层拦截？
- [ ] 业务异常（domain 抛出）与技术异常（infrastructure 抛出）是否有清晰的异常类型体系？是否会在 infrastructure 层做"技术异常 → 领域异常"的转译，避免技术细节泄漏到上层？
- [ ] 外部依赖不可用时（超时/限流/降级）的兜底策略是什么？

### 隐含约束（容易被忽略，必须主动确认）
- [ ] 幂等性：这个操作重复调用会不会产生副作用？是否需要幂等键？
- [ ] 并发：是否存在多个请求同时修改同一资源的竞态？需要乐观锁/悲观锁/分布式锁吗？
- [ ] 事务边界：这个用例涉及几个聚合根？跨聚合的一致性是强一致还是最终一致？
- [ ] 数据一致性：失败重试会不会导致重复写入？
- [ ] 边界值：数量为0、金额为负、时间跨零点/跨时区、分页边界等是否覆盖？
- [ ] 权限/多租户隔离：是否会误跨租户/跨用户访问数据？

### 及时反馈原则
- 上述任一项存在歧义或未被需求明确覆盖，**先提出问题，等待确认后再落地实现**，不要脑补一个"看起来合理"的默认行为直接写死在代码里（尤其是资金、库存、权限相关的隐含约束）。
- 若因为工期原因必须先做假设推进，需要在代码注释和验收文档中显式标注 `// ASSUMPTION: ...`，方便后续追溯。

---

## 五、确定性验收标准与测试记录规范

### 验收标准写法（Given / When / Then）
每个用例的验收标准必须是可执行、可验证的，禁止用"应该正常工作"这类模糊描述。

```
场景：订单支付成功后扣减库存
Given: 订单状态为"待支付"，商品库存为 5
When: 支付网关回调通知支付成功
Then: 订单状态变为"已支付"，商品库存变为 4，且发布"库存已扣减"领域事件
```

### 测试用例记录表（每次交付必须附带）

| 用例ID | 层级 | 场景描述 | 输入 | 预期结果 | 实际结果 | 状态 | 覆盖的边界/约束 |
|---|---|---|---|---|---|---|---|
| TC-001 | domain | 订单满100减20 | amount=150 | discount=20 | 20 | Pass | 边界值：99/100/100.01 |
| TC-002 | application | 支付回调编排 | 已mock仓储 | 调用顺序符合预期 | 一致 | Pass | 幂等：重复回调不重复扣库存 |
| TC-003 | infrastructure | Redis 库存扣减 | 并发2个请求 | 库存不为负 | 通过 | Pass | 并发/竞态 |

### 交付前的最终检查
- [ ] 所有测试用例均经历过完整 Red → Green → Refactor，且有记录（不是补写的"事后测试"）。
- [ ] 边界与隐含约束清单（第四节）逐项过了一遍，未覆盖项已反馈确认或已标注 ASSUMPTION。
- [ ] 依赖方向检查：domain 无外部依赖，infrastructure 只实现 domain 定义的抽象；application 对 infrastructure 的直接调用仅限纯技术编排能力（事务/锁/事件发布等），凡是有业务语义的能力仍通过 domain 抽象注入，未出现反向依赖（domain 依赖 application/infrastructure）。
- [ ] 测试记录表已附上，覆盖正常路径 + 至少一个异常路径 + 至少一个边界值。

---

## 六、目录结构参考示例（语言无关，示意）

```
src/
  interface/
    http/OrderController
    mq/PaymentCallbackConsumer
  application/
    PayOrderApplicationService
  domain/
    order/
      Order.entity
      OrderRepository.interface   # 抽象
      OrderPolicy.service         # 业务规则，纯逻辑
    notification/
      NotificationGateway.interface  # 抽象
  infrastructure/
    persistence/
      MySQLOrderRepository        # 实现 OrderRepository
    notification/
      SmsNotificationGateway       # 实现 NotificationGateway
    payment/
      ThirdPartyPaymentClient
```