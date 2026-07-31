const canvas = document.getElementById('bg-animation');
const ctx = canvas.getContext('2d');

let w, h;
let time = 0;
let mouseX = 0;
let mouseY = 0;

function resize() {
    w = canvas.width = window.innerWidth;
    h = canvas.height = window.innerHeight;
}

window.addEventListener('resize', resize);
window.addEventListener('mousemove', (e) => {
    mouseX = (e.clientX / w - 0.5) * 2;
    mouseY = (e.clientY / h - 0.5) * 2;
});
resize();

class WavePoint {
    constructor(x, y, index) {
        this.baseX = x;
        this.baseY = y;
        this.x = x;
        this.y = y;
        this.index = index;
    }
    
    update() {
        const offset = Math.sin(time * 2 + this.baseX * 0.01 + this.baseY * 0.01) * 30;
        this.y = this.baseY + offset;
        
        // Interactive wave based on mouse proximity
        const dx = this.baseX - (mouseX * w / 2 + w / 2);
        const dy = this.baseY - (mouseY * h / 2 + h / 2);
        const dist = Math.sqrt(dx*dx + dy*dy);
        if (dist < 200) {
            this.y -= (200 - dist) * 0.2;
        }
    }
}

const cols = 30;
const rows = 20;
const spacingX = 60;
const spacingY = 60;
const points = [];

for (let i = 0; i < cols; i++) {
    for (let j = 0; j < rows; j++) {
        // Center the grid
        const x = (w - (cols * spacingX)) / 2 + i * spacingX;
        const y = (h - (rows * spacingY)) / 2 + j * spacingY;
        points.push(new WavePoint(x, y, i * rows + j));
    }
}

function getPoint(i, j) {
    if (i < 0 || i >= cols || j < 0 || j >= rows) return null;
    return points[i * rows + j];
}

function animate() {
    ctx.clearRect(0, 0, w, h);
    time += 0.01;

    points.forEach(p => p.update());

    // Draw the mesh
    for (let i = 0; i < cols; i++) {
        for (let j = 0; j < rows; j++) {
            const p = getPoint(i, j);
            if (!p) continue;

            const right = getPoint(i + 1, j);
            const bottom = getPoint(i, j + 1);

            ctx.lineWidth = 1;
            
            // Pulse color effect based on y offset
            const intensity = Math.max(0, (p.baseY - p.y) / 30);
            
            if (right) {
                ctx.beginPath();
                ctx.moveTo(p.x, p.y);
                ctx.lineTo(right.x, right.y);
                ctx.strokeStyle = `rgba(16, 185, 129, ${0.1 + intensity * 0.4})`; // Emerald accents
                ctx.stroke();
            }
            if (bottom) {
                ctx.beginPath();
                ctx.moveTo(p.x, p.y);
                ctx.lineTo(bottom.x, bottom.y);
                ctx.strokeStyle = `rgba(37, 99, 235, ${0.1 + intensity * 0.4})`; // Blue accents
                ctx.stroke();
            }
            
            // Draw nodes at intersections with high intensity
            if (intensity > 0.5) {
                ctx.beginPath();
                ctx.arc(p.x, p.y, intensity * 2, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(6, 182, 212, ${intensity})`; // Cyan nodes
                ctx.fill();
            }
        }
    }

    requestAnimationFrame(animate);
}

animate();
