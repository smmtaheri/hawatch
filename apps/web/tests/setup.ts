import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";

import { clearDayCache } from "../src/lib/dayCache";
beforeEach(() => {
 clearDayCache();
 Object.defineProperty(window, "scrollTo", {configurable:true, value:vi.fn()});
 Object.defineProperty(HTMLDialogElement.prototype, "showModal", {configurable:true, value:function(this:HTMLDialogElement){this.setAttribute("open", "");}});
 Object.defineProperty(HTMLDialogElement.prototype, "close", {configurable:true, value:function(this:HTMLDialogElement){this.removeAttribute("open");}});
});
afterEach(() => {
  cleanup();
});
