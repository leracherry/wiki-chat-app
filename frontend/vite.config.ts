import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'node:fs'
import path from 'node:path'
import dotenv from 'dotenv'
import dotenvExpand from 'dotenv-expand'

function loadRootEnv(mode?: string) {
  const root = path.resolve(__dirname, '..')
  const files: string[] = [
    path.join(root, '.env'),
    path.join(root, '.env.local'),
  ]
  if (mode) {
    files.push(
      path.join(root, `.env.${mode}`),
      path.join(root, `.env.${mode}.local`),
    )
  }
  for (const file of files) {
    if (!fs.existsSync(file)) continue
    const result = dotenv.config({ path: file })
    dotenvExpand.expand(result)
  }
}

export default defineConfig(({ mode }) => {
  // Load root envs first so frontend/.env can override
  loadRootEnv(mode)

  return {
    plugins: [react()],
    server: { port: 3000, host: true },
    preview: { port: 3000, host: true },
    build: { outDir: 'dist', sourcemap: true },
    envPrefix: 'VITE_',
  }
})
