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

class FloatingCube {
    constructor() {
        this.x = Math.random() * w;
        this.y = Math.random() * h;
        this.z = Math.random() * 2 + 0.5;
        this.size = (Math.random() * 30 + 10) * this.z;
        this.rx = Math.random() * Math.PI;
        this.ry = Math.random() * Math.PI;
        this.vx = (Math.random() - 0.5) * 0.5;
        this.vy = -Math.random() * 1.5 - 0.5; // Float upwards
        this.drx = (Math.random() - 0.5) * 0.05;
        this.dry = (Math.random() - 0.5) * 0.05;
        
        // Holographic colors
        const isCyan = Math.random() > 0.5;
        this.color = isCyan ? 'rgba(6, 182, 212,' : 'rgba(37, 99, 235,';
    }

    update() {
        this.x += this.vx * this.z;
        this.y += this.vy * this.z;
        this.rx += this.drx;
        this.ry += this.dry;

        if (this.y < -100) {
            this.y = h + 100;
            this.x = Math.random() * w;
        }
    }

    draw() {
        const px = this.x - mouseX * 50 * this.z;
        const py = this.y - mouseY * 50 * this.z;
        
        ctx.save();
        ctx.translate(px, py);
        ctx.rotate(this.rx);
        // Simple 3D projection for a cube wireframe
        ctx.strokeStyle = `${this.color} ${0.3 * this.z})`;
        ctx.lineWidth = 1.5;
        ctx.shadowBlur = 10 * this.z;
        ctx.shadowColor = `${this.color} 0.5)`;
        
        const s = this.size;
        ctx.strokeRect(-s/2, -s/2, s, s);
        ctx.beginPath();
        ctx.moveTo(-s/2, -s/2); ctx.lineTo(-s/2 + s*0.3, -s/2 - s*0.3);
        ctx.moveTo(s/2, -s/2); ctx.lineTo(s/2 + s*0.3, -s/2 - s*0.3);
        ctx.moveTo(s/2, s/2); ctx.lineTo(s/2 + s*0.3, s/2 - s*0.3);
        ctx.moveTo(-s/2, s/2); ctx.lineTo(-s/2 + s*0.3, s/2 - s*0.3);
        ctx.stroke();
        
        ctx.strokeRect(-s/2 + s*0.3, -s/2 - s*0.3, s, s);
        
        ctx.restore();
    }
}

const cubes = Array.from({length: 40}, () => new FloatingCube());

function animate() {
    ctx.clearRect(0, 0, w, h);
    time += 0.01;

    // Draw animated gradient scanning beam
    const beamY = (Math.sin(time) * 0.5 + 0.5) * h;
    const grad = ctx.createLinearGradient(0, beamY - 100, 0, beamY + 100);
    grad.addColorStop(0, 'rgba(6, 182, 212, 0)');
    grad.addColorStop(0.5, 'rgba(6, 182, 212, 0.05)');
    grad.addColorStop(1, 'rgba(6, 182, 212, 0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);

    // Draw glowing data streams (vertical lines)
    for(let i=0; i<w; i+=80) {
        ctx.beginPath();
        ctx.moveTo(i, 0);
        ctx.lineTo(i, h);
        ctx.strokeStyle = `rgba(37, 99, 235, 0.03)`;
        ctx.lineWidth = 1;
        ctx.stroke();
    }

    cubes.forEach(c => {
        c.update();
        c.draw();
    });

    requestAnimationFrame(animate);
}

animate();
