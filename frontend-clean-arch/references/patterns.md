# 框架集成方案参考

## React + Zustand

Store 存储原始 Domain 实体，View Model 逻辑放在 selector 中。

```ts
// store/orderStore.ts
interface OrderStore {
  orders: Record<string, Order>;       // 原始 domain 实体
  fetchOrder: (id: string) => Promise<void>;
  cancelOrder: (id: string) => Promise<void>;
}

export const useOrderStore = create<OrderStore>((set, get) => ({
  orders: {},
  fetchOrder: async (id) => {
    const order = await orderRepo.findById(id);
    set(state => ({ orders: { ...state.orders, [id]: order } }));
  },
  cancelOrder: async (id) => {
    await cancelOrderUseCase(id, orderRepo);
    await get().fetchOrder(id); // 刷新
  },
}));

// view-models/orderViewModel.ts —— 永远是同一个纯函数
export const toOrderViewModel = (order: Order): OrderViewModel => ({ ... });

// hooks/useOrder.ts —— selector + vm 组合
export const useOrder = (id: string) => {
  const raw = useOrderStore(state => state.orders[id]);
  const fetchOrder = useOrderStore(state => state.fetchOrder);
  const cancelOrder = useOrderStore(state => state.cancelOrder);

  useEffect(() => { fetchOrder(id); }, [id]);

  return {
    vm: raw ? toOrderViewModel(raw) : null,
    cancel: () => cancelOrder(id),
  };
};
```

---

## Vue 3 + Pinia

```ts
// stores/orderStore.ts
export const useOrderStore = defineStore('order', {
  state: () => ({ orders: {} as Record<string, Order> }),
  actions: {
    async fetch(id: string) {
      this.orders[id] = await orderRepo.findById(id);
    },
    async cancel(id: string) {
      await cancelOrderUseCase(id, orderRepo);
      await this.fetch(id);
    },
  },
});

// composables/useOrder.ts —— Vue 的 "hooks"
export const useOrder = (id: string) => {
  const store = useOrderStore();
  onMounted(() => store.fetch(id));

  const vm = computed(() =>
    store.orders[id] ? toOrderViewModel(store.orders[id]) : null
  );

  return { vm, cancel: () => store.cancel(id) };
};
```

---

## React Query 方案

使用 React Query 时，query 本身替代了 store，ViewModel 层完全不变。

```ts
// hooks/useOrder.ts
export const useOrder = (id: string) => {
  const { data: raw, isLoading, error } = useQuery({
    queryKey: ['order', id],
    queryFn: () => orderRepo.findById(id),
  });

  const mutation = useMutation({ mutationFn: () => cancelOrderUseCase(id, orderRepo) });

  return {
    vm: raw ? toOrderViewModel(raw) : null,
    loading: isLoading,
    error,
    cancel: mutation.mutate,
  };
};
```

核心结论：`toOrderViewModel` 永远与框架无关，随框架/数据请求库变化的只有 hook 的外壳。

---

## 测试配方

### Domain 规则 —— 零配置
```ts
it('只有 pending 状态可以取消', () => {
  expect(canCancelOrder({ status: 'pending', ...rest })).toBe(true);
  expect(canCancelOrder({ status: 'paid', ...rest })).toBe(false);
});
```

### ViewModel —— 零配置
```ts
it('正确格式化总金额', () => {
  const vm = toOrderViewModel({ totalCents: 29900, status: 'pending', ...rest });
  expect(vm.formattedTotal).toBe('¥299.00');
  expect(vm.canCancel).toBe(true);
});
```

### Use Case —— 内存仓储，不需要 mock 库
```ts
class InMemoryOrderRepo implements IOrderRepository {
  private store = new Map<string, Order>();
  async findById(id: string) { return this.store.get(id)!; }
  async save(order: Order) { this.store.set(order.id, order); }
}

it('取消一个 pending 订单', async () => {
  const repo = new InMemoryOrderRepo();
  await repo.save({ id: '1', status: 'pending', ...rest });
  await cancelOrderUseCase('1', repo);
  expect((await repo.findById('1')).status).toBe('cancelled');
});
```

### 组件 —— 传入 mock vm，简单直接
```tsx
it('只有可取消订单才显示取消按钮', () => {
  const vm: OrderViewModel = { canCancel: true, statusLabel: '待支付', ... };
  render(<OrderCard vm={vm} onCancel={jest.fn()} />);
  expect(screen.getByText('取消订单')).toBeInTheDocument();
});
```