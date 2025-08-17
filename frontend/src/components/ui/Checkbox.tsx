import type { InputHTMLAttributes } from 'react'

interface Props extends Omit<InputHTMLAttributes<HTMLInputElement>, 'onChange'> {
  onChange?: (checked: boolean) => void
}

export function Checkbox({ onChange, ...props }: Props) {
  return (
    <input
      {...props}
      type="checkbox"
      onChange={(e) => onChange?.(e.currentTarget.checked)}
      className="h-4 w-4 text-brand-base focus:ring-brand-base/50 border-cohere-border rounded align-middle"
    />
  )
}

