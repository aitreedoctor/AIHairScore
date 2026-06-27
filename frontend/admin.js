const API_BASE = '/api/v1/scalp';

let adminChart = null;

document.addEventListener('DOMContentLoaded', () => {
    initAdmin();
});

function initAdmin() {
    registerAdminEvents();
    loadDashboardData();
}

function registerAdminEvents() {
    // Menu tab switching
    const sidebarButtons = document.querySelectorAll('.sidebar-btn');
    const panes = document.querySelectorAll('.admin-pane');

    sidebarButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const targetPaneId = e.currentTarget.getAttribute('data-pane');
            
            sidebarButtons.forEach(b => b.classList.remove('active'));
            panes.forEach(p => p.classList.remove('active'));
            
            e.currentTarget.classList.add('active');
            document.getElementById(targetPaneId).classList.add('active');

            if (targetPaneId === 'pane-stats') {
                loadDashboardData();
            } else if (targetPaneId === 'pane-db') {
                loadDbLogs();
            }
        });
    });

    // Safety filter playground test
    const btnTest = document.getElementById('btn-test-filter');
    btnTest.addEventListener('click', testSafetyFilter);
}

// Load statistics and charts
async function loadDashboardData() {
    try {
        const resp = await fetch(`${API_BASE}/history?user_id=all`);
        if (!resp.ok) throw new Error('이력 데이터를 가져오는 데 실패했습니다.');
        
        const history = await resp.json();
        
        // 1. Update metric widgets
        const totalScans = history.length;
        document.getElementById('stat-total-scans').textContent = totalScans;

        if (totalScans > 0) {
            const sumScore = history.reduce((acc, h) => acc + h.overall_score, 0);
            const avgScore = Math.round(sumScore / totalScans);
            document.getElementById('stat-avg-score').textContent = `${avgScore}점`;

            const warningCount = history.filter(h => h.overall_score <= 50).length;
            const warningRate = Math.round((warningCount / totalScans) * 100);
            document.getElementById('stat-warning-rate').textContent = `${warningRate}%`;
            
            renderAdminWarningChart(history);
        } else {
            document.getElementById('stat-avg-score').textContent = '0점';
            document.getElementById('stat-warning-rate').textContent = '0%';
            renderAdminWarningChart([]);
        }
    } catch (err) {
        console.error('Error loading dashboard stats:', err);
    }
}

// Render Admin Summary chart
function renderAdminWarningChart(history) {
    const ctx = document.getElementById('adminWarningChart').getContext('2d');
    if (adminChart) {
        adminChart.destroy();
    }

    if (history.length === 0) {
        return;
    }

    // Calculate average metrics across all diagnostic logs
    const total = history.length;
    const avgRedness = (history.reduce((acc, h) => acc + h.redness, 0) / total).toFixed(2);
    const avgDeadSkin = (history.reduce((acc, h) => acc + h.dead_skin, 0) / total).toFixed(2);
    const avgSebum = (history.reduce((acc, h) => acc + h.sebum, 0) / total).toFixed(2);
    const avgDensity = (history.reduce((acc, h) => acc + h.hair_density, 0) / total).toFixed(2);
    const avgThickness = (history.reduce((acc, h) => acc + h.hair_thickness, 0) / total).toFixed(2);

    adminChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['홍반(붉은기) 평균', '각질(비듬) 평균', '피지(유분) 평균', '모발 밀도 평균', '모발 굵기 평균'],
            datasets: [{
                label: '전체 판독 수치 평균 (0: 양호, 3: 위험)',
                data: [avgRedness, avgDeadSkin, avgSebum, avgDensity, avgThickness],
                backgroundColor: [
                    'rgba(239, 68, 68, 0.45)', // Redness
                    'rgba(232, 121, 249, 0.45)', // Deadskin
                    'rgba(96, 165, 250, 0.45)',  // Sebum
                    'rgba(52, 211, 153, 0.45)',  // Density
                    'rgba(167, 139, 250, 0.45)'  // Thickness
                ],
                borderColor: [
                    '#ef4444',
                    '#e879f9',
                    '#60a5fa',
                    '#34d399',
                    '#a78bfa'
                ],
                borderWidth: 1.5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    min: 0,
                    max: 3,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#9ca3af', stepSize: 1 }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#9ca3af' }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

// Test Safety filter Regex replacers
async function testSafetyFilter() {
    const inputVal = document.getElementById('txt-play-input').value.trim();
    if (!inputVal) {
        alert('테스트할 텍스트를 입력해 주세요.');
        return;
    }

    const outputDiv = document.getElementById('div-play-output');
    const tag = document.getElementById('safety-status-tag');
    const tagText = document.getElementById('safety-status-text');

    outputDiv.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 필터 분석 중...';
    tag.style.display = 'none';

    try {
        const formData = new FormData();
        formData.append('text', inputVal);

        const resp = await fetch(`${API_BASE}/test-safety-filter`, {
            method: 'POST',
            body: formData
        });

        if (!resp.ok) throw new Error('안전성 분석 검사에 실패했습니다.');

        const data = await resp.json();
        
        // Render result highlights
        let highlighted = data.filtered;
        
        // Highlight keywords replaced
        const replacements = {
            "상태 분석": "진단",
            "관리 추천": "처방",
            "탈모 경향성": "탈모증",
            "개선 관리": "치료",
            "판독 완료": "확진",
            "케어 가이드": "의사",
            "케어 제안": "약처방"
        };

        for (const [after, before] of Object.entries(replacements)) {
            const regex = new RegExp(after, 'g');
            highlighted = highlighted.replace(regex, `<span class="replaced-word">${after}</span>`);
        }

        outputDiv.innerHTML = highlighted;

        // Display safety indicator tags
        tag.style.display = 'inline-flex';
        tag.className = 'violation-tag';
        
        if (data.is_safe && data.detected.length === 0) {
            tag.classList.add('safety-tag-pass');
            tagText.innerHTML = '<i class="fa-solid fa-circle-check"></i> 검열 통과: 위험 단어 미검출 (안전)';
        } else {
            tagText.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> 위험어 [${data.detected.join(', ')}] ${data.detected.length}개 자동 우회 치환 완료 (의료법 준수)`;
        }

    } catch (err) {
        outputDiv.textContent = `오류 발생: ${err.message}`;
    }
}

// Fetch and render database log rows
async function loadDbLogs() {
    const tableBody = document.getElementById('db-table-body');
    tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center;"><i class="fa-solid fa-circle-notch fa-spin"></i> DB 데이터 동기화 중...</td></tr>';

    try {
        const resp = await fetch(`${API_BASE}/history?user_id=all`);
        if (!resp.ok) throw new Error('DB 로그 조회 실패');

        const logs = await resp.json();

        if (logs.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">저장된 진단 데이터 로그가 없습니다.</td></tr>';
            return;
        }

        tableBody.innerHTML = '';
        logs.forEach(l => {
            const tr = document.createElement('tr');
            const ageDisplay = l.age !== undefined && l.age !== null ? `만 ${l.age}세` : '미입력';
            const genderDisplay = l.gender ? (l.gender.toLowerCase() === 'male' ? '남성' : '여성') : '미입력';
            tr.innerHTML = `
                <td><code>${l.id.substring(0, 8)}...</code></td>
                <td>${ageDisplay} / ${genderDisplay}</td>
                <td>홍반: ${l.redness} | 각질: ${l.dead_skin} | 피지: ${l.sebum}</td>
                <td>밀도: ${l.hair_density} | 굵기: ${l.hair_thickness}</td>
                <td><b>${l.overall_score}점</b> <span class="logo-badge" style="background: rgba(139,92,246,0.1); border-color: rgba(139,92,246,0.3); color: #a78bfa">${l.overall_grade}</span></td>
                <td>${l.created_at}</td>
            `;
            tableBody.appendChild(tr);
        });

    } catch (err) {
        tableBody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--danger);">오류 발생: ${err.message}</td></tr>`;
    }
}
