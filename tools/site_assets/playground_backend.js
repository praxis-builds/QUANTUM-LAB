"use strict";

// The Circuit Playground's backend on the static site: the dashboard's UI code (playground.js)
// asks window.PlaygroundBackend instead of the Python server. Same requests, same answers: exact
// states from circuit_sim.js (a port of circuit_playground.py), shots from a seeded browser PRNG
// ("browser sampling, not Aer"). Presets are exported from Python when the site is built (presets.js).
// Nothing leaves the browser.
(() => {
  const Sim = typeof PlaygroundSim !== "undefined" ? PlaygroundSim : globalThis.PlaygroundSim;
  globalThis.window = globalThis.window || globalThis;
  window.PlaygroundBackend = {
    label: Sim.SAMPLER,
    async simulate(body) {
      try {
        return {status: 200, ok: true, data: Sim.simulate(JSON.parse(body))};
      } catch (error) {
        if (error instanceof Sim.RequestError || error instanceof SyntaxError) return {status: 400, ok: false, data: {error: error.message}};
        throw error;
      }
    },
    async presets() {
      const presets = window.PLAYGROUND_PRESETS;
      return Array.isArray(presets) ? {status: 200, ok: true, data: {presets}} : {status: 500, ok: false, data: null};
    }
  };
})();
