import type { ButtonHTMLAttributes, PropsWithChildren } from 'react'
import { cx } from '../../utils/cx'

export function Button({ className, ...props }: PropsWithChildren<ButtonHTMLAttributes<HTMLButtonElement>>) {
  return (
    <button
      {...props}
      className={cx(
        'bg-brand-base hover:bg-brand-base/90 disabled:bg-ink/20 disabled:cursor-not-allowed text-white font-medium py-3 px-6 rounded-xl transition-colors duration-200',
        className,
      )}
    />
  )
}

