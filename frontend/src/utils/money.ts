import type { Money } from '../types/travel'

export function toNumber(value: Money | null | undefined): number {
  if (value === null || value === undefined) {
    return 0
  }
  return typeof value === 'number' ? value : Number(value)
}

export function formatMoney(value: Money | null | undefined, currency = 'CNY'): string {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0
  }).format(toNumber(value))
}

