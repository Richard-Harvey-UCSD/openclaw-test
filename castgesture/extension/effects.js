/**
 * CastGesture — DOM-based effects for injection into any page.
 * No canvas needed — uses CSS animations and DOM elements.
 */

const CastGestureEffects = (() => {
  let overlay = null;

  function getOverlay() {
    if (overlay && document.body.contains(overlay)) return overlay;
    overlay = document.createElement('div');
    overlay.id = 'castgesture-overlay';
    overlay.style.cssText = `
      position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
      pointer-events: none; z-index: 2147483647; overflow: hidden;
    `;
    document.body.appendChild(overlay);
    return overlay;
  }

  function createParticle(opts) {
    const el = document.createElement('div');
    const size = opts.size || (Math.random() * 8 + 4);
    const color = opts.color || '#a855f7';
    const startX = opts.x || 50;
    const startY = opts.y || 50;
    const angle = Math.random() * Math.PI * 2;
    const speed = (Math.random() * 200 + 100) * (opts.intensity || 1);
    const dx = Math.cos(angle) * speed;
    const dy = Math.sin(angle) * speed - 150;

    el.style.cssText = `
      position: absolute; width: ${size}px; height: ${size * 1.4}px;
      background: ${color}; border-radius: ${Math.random() > 0.5 ? '50%' : '2px'};
      left: ${startX}%; top: ${startY}%;
      pointer-events: none; will-change: transform, opacity;
    `;
    el.animate([
      { transform: 'translate(0, 0) rotate(0deg)', opacity: 1 },
      { transform: `translate(${dx}px, ${dy + 400}px) rotate(${Math.random()*720}deg)`, opacity: 0 },
    ], { duration: 2000 + Math.random() * 1000, easing: 'cubic-bezier(.25,.46,.45,.94)' })
      .onfinish = () => el.remove();

    return el;
  }

  function confetti(params = {}) {
    const o = getOverlay();
    const count = params.particle_count || 100;
    const colors = params.colors || ['#a855f7','#06b6d4','#f43f5e','#facc15','#22c55e','#3b82f6','#ec4899'];
    const x = (params.x || 0.5) * 100;
    const y = (params.y || 0.5) * 100;
    for (let i = 0; i < count; i++) {
      setTimeout(() => {
        o.appendChild(createParticle({
          x, y, size: Math.random() * 8 + 3,
          color: colors[Math.floor(Math.random() * colors.length)],
          intensity: params.intensity || 1,
        }));
      }, Math.random() * 100);
    }
  }

  function emojiRain(params = {}) {
    const o = getOverlay();
    const emoji = params.emoji || '✌️';
    const count = params.particle_count || 30;
    for (let i = 0; i < count; i++) {
      setTimeout(() => {
        const el = document.createElement('div');
        const x = Math.random() * 100;
        const size = Math.random() * 20 + 20;
        el.textContent = emoji;
        el.style.cssText = `
          position: absolute; left: ${x}%; top: -40px;
          font-size: ${size}px; pointer-events: none;
          will-change: transform, opacity;
        `;
        el.animate([
          { transform: 'translateY(0) rotate(0deg)', opacity: 1 },
          { transform: `translateY(${window.innerHeight + 60}px) rotate(${Math.random()*360}deg)`, opacity: 0.3 },
        ], { duration: 3000 + Math.random() * 2000, easing: 'ease-in' })
          .onfinish = () => el.remove();
        o.appendChild(el);
      }, i * 100);
    }
  }

  function screenShake(params = {}) {
    const intensity = params.intensity || 1;
    const dur = (params.duration || 0.5) * 1000;
    document.body.animate([
      { transform: 'translate(0,0)' },
      { transform: `translate(${-8*intensity}px,${-6*intensity}px)` },
      { transform: `translate(${8*intensity}px,${4*intensity}px)` },
      { transform: `translate(${-6*intensity}px,${8*intensity}px)` },
      { transform: `translate(${6*intensity}px,${-8*intensity}px)` },
      { transform: 'translate(0,0)' },
    ], { duration: dur, easing: 'ease-in-out' });
  }

  function flash(params = {}) {
    const o = getOverlay();
    const el = document.createElement('div');
    el.style.cssText = `
      position: absolute; top: 0; left: 0; width: 100%; height: 100%;
      background: white; pointer-events: none;
    `;
    el.animate([
      { opacity: 0.9 },
      { opacity: 0 },
    ], { duration: (params.duration || 0.3) * 1000 })
      .onfinish = () => el.remove();
    o.appendChild(el);
  }

  function textPop(params = {}) {
    const o = getOverlay();
    const el = document.createElement('div');
    el.textContent = params.text || 'NICE!';
    el.style.cssText = `
      position: absolute; top: 50%; left: 50%;
      transform: translate(-50%, -50%) scale(0.3);
      font-size: ${params.font_size || 80}px; font-weight: 900;
      color: white; pointer-events: none;
      text-shadow: 0 0 40px rgba(168,85,247,0.8), 0 4px 8px rgba(0,0,0,0.5);
      font-family: system-ui, -apple-system, sans-serif;
    `;
    const dur = (params.duration || 2) * 1000;
    el.animate([
      { transform: 'translate(-50%,-50%) scale(0.3)', opacity: 0 },
      { transform: 'translate(-50%,-50%) scale(1)', opacity: 1, offset: 0.15 },
      { transform: 'translate(-50%,-50%) scale(1)', opacity: 1, offset: 0.7 },
      { transform: 'translate(-50%,-60%) scale(1.2)', opacity: 0 },
    ], { duration: dur })
      .onfinish = () => el.remove();
    o.appendChild(el);
  }

  function fire(params = {}) {
    const o = getOverlay();
    const dur = (params.duration || 3) * 1000;
    const el = document.createElement('div');
    el.style.cssText = `
      position: absolute; bottom: 0; left: 0; width: 100%; height: 40%;
      background: linear-gradient(to top,
        rgba(255,100,0,0.6) 0%, rgba(255,160,20,0.3) 30%,
        rgba(255,60,0,0.1) 60%, transparent 100%);
      pointer-events: none;
    `;
    el.animate([
      { opacity: 0 }, { opacity: 1, offset: 0.1 },
      { opacity: 1, offset: 0.8 }, { opacity: 0 },
    ], { duration: dur })
      .onfinish = () => el.remove();
    o.appendChild(el);
  }

  function spotlight(params = {}) {
    const o = getOverlay();
    const x = (params.x || 0.5) * 100;
    const y = (params.y || 0.5) * 100;
    const el = document.createElement('div');
    el.style.cssText = `
      position: absolute; left: ${x}%; top: ${y}%;
      width: 300px; height: 300px; transform: translate(-50%,-50%);
      border-radius: 50%; pointer-events: none;
      background: radial-gradient(circle, rgba(168,85,247,0.3) 0%, transparent 70%);
      box-shadow: 0 0 60px 30px rgba(168,85,247,0.15);
    `;
    const dur = (params.duration || 3) * 1000;
    el.animate([
      { opacity: 0 }, { opacity: 1, offset: 0.1 },
      { opacity: 1, offset: 0.8 }, { opacity: 0 },
    ], { duration: dur })
      .onfinish = () => el.remove();
    o.appendChild(el);
  }

  return {
    trigger(effect, params = {}) {
      switch (effect) {
        case 'confetti': confetti(params); break;
        case 'emoji_rain': emojiRain(params); break;
        case 'screen_shake': screenShake(params); break;
        case 'flash': flash(params); break;
        case 'text_pop': textPop(params); break;
        case 'fire': fire(params); break;
        case 'spotlight': spotlight(params); break;
      }
    },
    cleanup() {
      if (overlay) { overlay.remove(); overlay = null; }
    },
  };
})();

// Export for content script
if (typeof window !== 'undefined') window.CastGestureEffects = CastGestureEffects;
