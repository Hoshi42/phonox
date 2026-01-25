/// <reference types="vite/client" />

declare namespace NodeJS {
  interface Timeout {
    ref(): this
    unref(): this
  }
}
