export function cx(...cls: Array<string | undefined | false | null>) {
  return cls.filter(Boolean).join(' ')
}

