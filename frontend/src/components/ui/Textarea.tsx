import type { TextareaHTMLAttributes } from 'react'
import { cx } from '../../utils/cx'

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={cx(
        'w-full px-4 py-3 border border-cohere-border rounded-xl bg-cohere-background shadow-sm placeholder:text-ink/40 focus:ring-2 focus:ring-brand-base/50 focus:border-brand-base resize-none',
        className,
      )}
    />
  )
}

