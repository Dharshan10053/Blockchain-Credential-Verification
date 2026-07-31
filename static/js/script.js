/* CertAuth — frontend interactions */

document.addEventListener("DOMContentLoaded", () => {
  initUploadZone();
  initForms();
  animateConfidenceBar();
});


/* ── Drag-and-drop upload zone ───────────────────────────── */
function initUploadZone() {
  const zone  = document.querySelector(".upload-zone");
  const input = zone?.querySelector("input[type=file]");
  const label = document.querySelector(".file-selected");

  if (!zone || !input) return;

  ["dragenter", "dragover"].forEach(e =>
    zone.addEventListener(e, ev => { ev.preventDefault(); zone.classList.add("drag-over"); })
  );

  ["dragleave", "dragend", "drop"].forEach(e =>
    zone.addEventListener(e, () => zone.classList.remove("drag-over"))
  );

  zone.addEventListener("drop", ev => {
    ev.preventDefault();
    const files = ev.dataTransfer?.files;
    if (files?.length) {
      input.files = files;
      showSelected(files[0].name);
    }
  });

  input.addEventListener("change", () => {
    if (input.files.length) showSelected(input.files[0].name);
  });

  function showSelected(name) {
    if (!label) return;
    const span = label.querySelector("span");
    if (span) span.textContent = name;
    label.classList.add("show");
  }
}


/* ── Form loading state ──────────────────────────────────── */
function initForms() {
  document.querySelectorAll("form.upload-form").forEach(form => {
    form.addEventListener("submit", () => {
      const btn = form.querySelector("button[type=submit]");
      if (btn) {
        btn.classList.remove("btn-primary", "btn-secondary"); // Prevent color clash
        btn.classList.add("loading-shimmer");
        btn.disabled = true;
      }
      showGlobalLoader();
    });
  });
}

function showGlobalLoader() {
  const loader = document.getElementById("global-loader");
  if (!loader) return;
  
  loader.classList.add("active");
  
  const statusText = document.getElementById("loader-status-text");
  const hashText = document.getElementById("loader-hash-text");
  
  const statuses = [
    "Authenticating Certificate",
    "Verifying Authenticity",
    "Securing Blockchain Record"
  ];
  
  let step = 0;
  setInterval(() => {
    step = (step + 1) % statuses.length;
    if (statusText) {
      statusText.style.transition = 'opacity 1.2s cubic-bezier(0.16, 1, 0.3, 1)';
      statusText.style.opacity = '0';
      setTimeout(() => {
        statusText.textContent = statuses[step];
        statusText.style.opacity = '1';
      }, 1200); // Wait for slow cinematic fade out
    }
  }, 3500); // Calmer, slower intervals
  
  setInterval(() => {
    if (hashText) {
      let hash = "0x";
      const chars = "0123456789ABCDEF";
      for (let i = 0; i < 64; i++) hash += chars[Math.floor(Math.random() * 16)];
      hashText.textContent = hash;
    }
  }, 60);
  
  initLoaderCanvas();
}

function initLoaderCanvas() {
  const canvas = document.getElementById("loader-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d", { alpha: false });
  
  let w = canvas.width = window.innerWidth;
  let h = canvas.height = window.innerHeight;
  
  window.addEventListener("resize", () => {
    w = canvas.width = window.innerWidth;
    h = canvas.height = window.innerHeight;
  });
  
  const nodes = [];
  const numNodes = Math.min(Math.floor(w / 15), 60); // Responsive node count
  
  for (let i = 0; i < numNodes; i++) {
    nodes.push({
      x: Math.random() * w,
      y: Math.random() * h,
      z: Math.random() * 2 + 0.5, // Depth for parallax & scaling
      vx: (Math.random() - 0.5) * 0.15,
      vy: (Math.random() - 0.5) * 0.15 - 0.1, // Calmer, slower upward drift
      baseRadius: Math.random() * 2.5 + 1.5
    });
  }
  
  function draw() {
    // Elegant dark background fade for trailing effect
    ctx.fillStyle = "rgba(11, 17, 32, 1.0)";
    ctx.fillRect(0, 0, w, h);
    
    // Update and draw connections first so they sit behind nodes
    ctx.lineWidth = 1;
    for (let i = 0; i < nodes.length; i++) {
      let n1 = nodes[i];
      for (let j = i + 1; j < nodes.length; j++) {
        let n2 = nodes[j];
        let dx = n1.x - n2.x;
        let dy = n1.y - n2.y;
        let dist = Math.sqrt(dx * dx + dy * dy);
        
        if (dist < 180) {
          let alpha = (1 - dist / 180) * 0.35;
          // Use the brand cyan for connections
          ctx.strokeStyle = `rgba(6, 182, 212, ${alpha})`;
          ctx.beginPath();
          ctx.moveTo(n1.x, n1.y);
          ctx.lineTo(n2.x, n2.y);
          ctx.stroke();
        }
      }
    }
    
    // Draw nodes
    nodes.forEach(node => {
      // Parallax movement based on Z depth
      node.x += node.vx * node.z;
      node.y += node.vy * node.z;
      
      // Screen wrapping
      if (node.x < -10) node.x = w + 10;
      if (node.x > w + 10) node.x = -10;
      if (node.y < -10) node.y = h + 10;
      if (node.y > h + 10) node.y = -10;
      
      let radius = node.baseRadius * node.z;
      
      // Draw node glow
      let gradient = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, radius * 3);
      gradient.addColorStop(0, `rgba(37, 99, 235, ${0.8 * (node.z/2.5)})`); // Electric blue
      gradient.addColorStop(1, 'rgba(37, 99, 235, 0)');
      
      ctx.beginPath();
      ctx.arc(node.x, node.y, radius * 3, 0, Math.PI * 2);
      ctx.fillStyle = gradient;
      ctx.fill();
      
      // Draw solid core
      ctx.beginPath();
      ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(16, 185, 129, ${0.9 * (node.z/2.5)})`; // Emerald
      ctx.fill();
    });
    
    requestAnimationFrame(draw);
  }
  draw();
}


/* ── Confidence bar animation ────────────────────────────── */
function animateConfidenceBar() {
  const fill = document.querySelector(".confidence-fill");
  if (!fill) return;
  const target = fill.dataset.width || "0";
  // Briefly set to 0 then animate to target
  fill.style.width = "0%";
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      fill.style.width = target + "%";
    });
  });
}
