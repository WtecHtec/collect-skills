---
name: frontend-clean-arch
description: >
  将整洁架构原则应用到前端（React/Vue 等）项目中。
  当用户询问前端项目结构、代码架构、关注点分离、如何组织 domain 逻辑、hooks、
  utils 或组件时，使用此技能。即使用户只是随口说"这段逻辑放哪里？"、
  "我的 hooks 怎么组织？"、"组件越来越臃肿"、"业务逻辑怎么不写进 UI？"
  也要触发。当用户提到 domain、use-case、view-model、repository 模式，
  或任何前端分层架构概念时同样触发。
---

# 前端整洁架构 Skill

帮助用户设计并落地受整洁架构启发的前端分层方案。
各层为：**Domain → Use Case → View Model（Hooks）→ UI**，
**Utils** 作为无状态辅助层独立存在。

## 核心心智模型

```
┌─────────────────────────────┐  ← 最易变，强依赖框架
│            UI               │    组件、页面、样式
├─────────────────────────────┤
│      View Model / Hooks     │    toXxxViewModel() + useXxx() hooks
├─────────────────────────────┤
│         Use Case            │    业务流程编排
├─────────────────────────────┤
│          Domain             │  ← 最稳定，零框架依赖
│  实体 · 业务规则 · IRepo    │
└─────────────────────────────┘
          Utils（纯函数，不依赖任何层）
```

**依赖规则**：外层可以导入内层，内层绝不导入外层。Domain 层零框架 import。

---

## 各层定义

### Domain（领域层）
业务核心。纯 TypeScript/JavaScript —— 不引入 React、Vue、fetch。

- **实体（Entities）**：反映业务概念的数据结构（`Order`、`User`）
- **业务规则（Business Rules）**：表达领域不变量的纯函数（`canCancelOrder`、`isEligibleForDiscount`）
- **仓储接口（Repository Interfaces）**：数据访问契约（只有接口，没有实现）
- **领域事件 / 错误（Domain Events / Errors）**：类型化的事件与错误类

```ts
// domain/entities/order.ts
export interface Order {
  id: string;
  items: OrderItem[];
  status: 'pending' | 'paid' | 'shipped' | 'cancelled';
  totalCents: number;
}

// domain/rules/orderRules.ts
export const canCancelOrder = (order: Order): boolean =>
  order.status === 'pending';

// domain/repositories/IOrderRepository.ts
export interface IOrderRepository {
  findById(id: string): Promise<Order>;
  save(order: Order): Promise<void>;
}
```

---

### Use Case（用例层）
编排业务流程。只依赖 Domain 接口，不依赖具体基础设施或 UI。

- 每个类/函数对应一个用户意图（`PlaceOrderUseCase`、`CancelOrderUseCase`）
- 接收 DTO（普通对象），返回结果
- 负责校验、抛错、副作用排序

```ts
// use-cases/cancelOrder.ts
export const cancelOrder = async (
  orderId: string,
  repo: IOrderRepository,
): Promise<void> => {
  const order = await repo.findById(orderId);
  if (!canCancelOrder(order)) throw new DomainError('该订单不可取消');
  await repo.save({ ...order, status: 'cancelled' });
};
```

---

### View Model + Hooks（视图模型层）

这是前端整洁架构的核心洞察：**拆成两部分**。

**第一部分 —— `toXxxViewModel()` 纯函数**
将原始 Domain 实体映射为 UI 所需的展示结构。没有 hooks，没有副作用，可独立单测。

```ts
// view-models/orderViewModel.ts
export interface OrderViewModel {
  id: string;
  statusLabel: string;      // '待支付' 而非 'pending'
  statusColor: string;      // '#F59E0B'
  formattedTotal: string;   // '¥ 299.00'
  canCancel: boolean;       // 调用 domain 规则
  itemCount: string;        // '共 3 件'
}

export const toOrderViewModel = (order: Order): OrderViewModel => ({
  id: order.id,
  statusLabel: ORDER_STATUS_LABELS[order.status],
  statusColor: ORDER_STATUS_COLORS[order.status],
  formattedTotal: formatCurrency(order.totalCents),
  canCancel: canCancelOrder(order),           // ← 复用 domain 规则
  itemCount: `共 ${order.items.length} 件`,
});
```

**第二部分 —— `useXxx()` hook**
hook 是 ViewModel 的*运行容器*：取数据、调用 `toXxxViewModel()`、
管理 UI 状态（`loading`、`error`）、暴露 Use Case 动作。

```ts
// hooks/useOrder.ts
export const useOrder = (orderId: string) => {
  const [vm, setVm] = useState<OrderViewModel | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    orderRepo.findById(orderId)
      .then(order => setVm(toOrderViewModel(order)))   // ← 在这里组合
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [orderId]);

  const cancel = async () => {
    await cancelOrder(orderId, orderRepo);
    // 刷新数据
  };

  return { vm, loading, error, cancel };
};
```

> **为什么要拆？** 纯函数 `toXxxViewModel` 无需任何 mock 即可单元测试。
> hook 只负责编排。组件保持纯粹的展示职责。

---

### UI（展示层）
纯展示。消费 ViewModel props，永远不接触原始 Domain 数据。

- **组件（Components）**：无状态，只接收 `vm` props
- **容器 / 页面（Containers / Pages）**：调用 `useXxx()`，将 `vm` 向下传递
- 不写业务逻辑，不做格式化，不调用 domain 规则

```tsx
// ui/components/OrderCard.tsx
const OrderCard = ({ vm, onCancel }: { vm: OrderViewModel; onCancel: () => void }) => (
  <div>
    <span style={{ color: vm.statusColor }}>{vm.statusLabel}</span>
    <span>{vm.formattedTotal}</span>
    <span>{vm.itemCount}</span>
    {vm.canCancel && <button onClick={onCancel}>取消订单</button>}
  </div>
);

// ui/pages/OrderPage.tsx
const OrderPage = ({ id }: { id: string }) => {
  const { vm, loading, error, cancel } = useOrder(id);
  if (loading) return <Spinner />;
  if (error || !vm) return <ErrorView />;
  return <OrderCard vm={vm} onCancel={cancel} />;
};
```

---

### Utils（工具层）
零层依赖的纯函数。可跨项目复用。

- 格式化：`formatCurrency`、`formatDate`、`formatRelativeTime`
- 校验：`isValidEmail`、`isValidPhone`
- 辅助函数：数组 / 对象 / 字符串操作
- 常量与枚举

```ts
// utils/currency.ts
export const formatCurrency = (cents: number, currency = 'CNY'): string =>
  new Intl.NumberFormat('zh-CN', { style: 'currency', currency })
    .format(cents / 100);
```

---

## 目录结构

```
src/
├── domain/
│   ├── entities/
│   ├── rules/
│   └── repositories/       # 只有接口
├── use-cases/
├── view-models/             # toXxxViewModel 纯函数
├── hooks/                   # useXxx hooks（组合 VM + use-case）
├── ui/
│   ├── components/          # 无状态，纯 props
│   └── pages/               # 调用 hooks，向下传 vm
├── infrastructure/
│   └── repositories/        # IRepo 的具体实现
└── utils/
```

---

## 常见反模式识别

| 反模式 | 问题 | 修复方案 |
|---|---|---|
| 业务规则写在 JSX | `order.status === 'pending' && <button>` | 移到 domain，通过 `vm.canCancel` 暴露 |
| 格式化写在组件 | `(price / 100).toFixed(2)` 在 JSX 中 | 移到 `toXxxViewModel` 或 utils |
| 叶子组件直接调 API | `useEffect(() => fetch(...))` 写在叶子组件 | 提升到 hook，向下传 vm |
| 臃肿的 hook 内联映射 | 映射逻辑直接写在 `useEffect` 回调里 | 提取为 `toXxxViewModel` 纯函数 |
| Domain 层 import React | 实体文件里 `import { useState }` | Domain 必须零框架依赖 |

---

## 场景导航

**"我的组件越来越臃肿"**
→ 检查 JSX 里是否有业务规则或格式化逻辑，提取到 domain 规则和 `toXxxViewModel`。

**"这段逻辑应该放哪里？"**
→ 依次问：是业务不变量（domain 规则）？是流程编排（use-case）？
是展示转换（view-model）？是通用工具（utils）？

**"怎么测试？"**
→ `toXxxViewModel` = 纯函数单测，零 mock。
→ Use Case = 用内存仓储测试（用 Map 实现 `IRepository`）。
→ Domain 规则 = 纯函数测试。
→ 组件 = 传入 mock vm 做快照或交互测试。

**"我在用 Zustand / Pinia / Redux"**
→ Store 存原始 Domain 实体。Selector 就是 View Model 层：
写 `selectOrderViewModel(state)` selector，内部调用 `toOrderViewModel`，
hook 消费 selector。

详见 `references/patterns.md`，包含 React + Zustand、Vue + Pinia 的具体集成方案。