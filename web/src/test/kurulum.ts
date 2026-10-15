// Her test dosyasından önce çalışır (vite.config.ts: test.setupFiles).
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";
import { sunucu } from "./sunucu";

// jsdom (tarayıcı taklidi) <dialog>'un showModal/close yöntemlerini bilmez; basit bir taklit.
if (typeof HTMLDialogElement !== "undefined" && !HTMLDialogElement.prototype.showModal) {
  HTMLDialogElement.prototype.showModal = function showModal(this: HTMLDialogElement) {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function close(this: HTMLDialogElement) {
    this.removeAttribute("open");
    this.dispatchEvent(new Event("close"));
  };
}

// Sahte API: tanımlanmamış bir isteğe test hata versin (sessizce gerçek ağa gitmesin).
beforeAll(() => sunucu.listen({ onUnhandledFrame: "error" }));
afterEach(() => {
  cleanup();
  sunucu.resetHandlers();
});
afterAll(() => sunucu.close());
