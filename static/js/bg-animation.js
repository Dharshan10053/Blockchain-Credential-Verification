const canvas = document.getElementById('bg-animation');
const ctx = canvas.getContext('2d');

let width, height;
let particles = [];
const PARTICLE_COUNT = 150;
const CONNECTION_DISTANCE = 180;

let mouseX = 0;
let mouseY = 0;

function resize() {
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = width;
    canvas.height = height;
}

window.addEventListener('resize', resize);
window.addEventListener('mousemove', (e) => {
    mouseX = e.clientX - width / 2;
    mouseY = e.clientY - height / 2;
});
resize();

class Particle {
    constructor() {
        this.x = Math.random() * width;
        this.y = Math.random() * height;
        this.z = Math.random() * 2 + 0.2; // depth factor (0.2 to 2.2)
        this.vx = (Math.random() - 0.5) * 1.2;
        this.vy = (Math.random() - 0.5) * 1.2;
        
        // Base radius based on depth (closer = larger)
        this.baseRadius = (Math.random() * 1.5 + 1) * this.z;
        this.radius = this.baseRadius;
        
        // Bright blue and cyan
        const isCyan = Math.random() > 0.4;
        this.baseColor = isCyan ? [6, 182, 212] : [37, 99, 235]; 
        
        this.pulsePhase = Math.random() * Math.PI * 2;
        this.pulseSpeed = Math.random() * 0.04 + 0.01;
    }

    update() {
        this.x += this.vx * this.z; 
        this.y += this.vy * this.z;
        
        // Pulse effect
        this.pulsePhase += this.pulseSpeed;
        const pulse = (Math.sin(this.pulsePhase) + 1) / 2; // 0 to 1
        this.radius = this.baseRadius + pulse * 1.5 * this.z;

        // Wrap around smoothly
        const padding = 150;
        if (this.x < -padding) this.x = width + padding;
        if (this.x > width + padding) this.x = -padding;
        if (this.y < -padding) this.y = height + padding;
        if (this.y > height + padding) this.y = -padding;
    }

    draw() {
        // Parallax offset based on mouse
        const px = this.x - mouseX * this.z * 0.03;
        const py = this.y - mouseY * this.z * 0.03;
        
        const alpha = Math.min(1, this.z * 0.4 + 0.1); 
        
        ctx.beginPath();
        ctx.arc(px, py, this.radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${this.baseColor[0]}, ${this.baseColor[1]}, ${this.baseColor[2]}, ${alpha})`;
        
        // Clear glowing effect
        ctx.shadowBlur = 12 * this.z;
        ctx.shadowColor = `rgba(${this.baseColor[0]}, ${this.baseColor[1]}, ${this.baseColor[2]}, ${alpha * 0.8})`;
        ctx.fill();
        ctx.shadowBlur = 0;
    }
}

for (let i = 0; i < PARTICLE_COUNT; i++) {
    particles.push(new Particle());
}

function animate() {
    ctx.clearRect(0, 0, width, height);

    for (let i = 0; i < particles.length; i++) {
        particles[i].update();
        particles[i].draw();

        for (let j = i + 1; j < particles.length; j++) {
            // Only connect if z difference is small to maintain 3D layered look
            const dz = Math.abs(particles[i].z - particles[j].z);
            if (dz > 0.8) continue;

            const px1 = particles[i].x - mouseX * particles[i].z * 0.03;
            const py1 = particles[i].y - mouseY * particles[i].z * 0.03;
            const px2 = particles[j].x - mouseX * particles[j].z * 0.03;
            const py2 = particles[j].y - mouseY * particles[j].z * 0.03;

            const dx = px1 - px2;
            const dy = py1 - py2;
            const distance = Math.sqrt(dx * dx + dy * dy);

            // Scale connection distance by depth
            const avgZ = (particles[i].z + particles[j].z) / 2;
            const maxDist = CONNECTION_DISTANCE * avgZ;

            if (distance < maxDist) {
                ctx.beginPath();
                ctx.moveTo(px1, py1);
                ctx.lineTo(px2, py2);
                
                const opacity = (1 - (distance / maxDist)) * 0.35 * avgZ;
                
                // Flowing energy effect
                if (distance > 50) {
                    ctx.setLineDash([10 * avgZ, 20 * avgZ]);
                    ctx.lineDashOffset = -(Date.now() / 50) * avgZ;
                } else {
                    ctx.setLineDash([]);
                }
                
                ctx.strokeStyle = `rgba(6, 182, 212, ${opacity})`;
                ctx.lineWidth = 1 * avgZ;
                ctx.stroke();
                ctx.setLineDash([]);
            }
        }
    }

    requestAnimationFrame(animate);
}

animate();
