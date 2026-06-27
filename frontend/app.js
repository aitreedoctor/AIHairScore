// API base URL configuration
const API_BASE = '/api/v1/scalp';

// App state management
const state = {
    currentScreen: 'screen-welcome',
    currentStep: 1,
    profile: {
        name: '박지성',
        age: 28,
        gender: 'male',
        family_history: 'paternal_side',
        location: '서울시 강남구'
    },
    symptoms: [],
    scanMode: 'upload', // 'upload' | 'sim'
    selectedFileCrown: null,
    selectedFileFront: null,
    selectedFileBack: null,
    isAiAnalyzed: false,
    visionScores: {
        redness: 1,
        dead_skin: 1,
        sebum: 2,
        hair_density: 2,
        hair_thickness: 2
    },
    latestReport: null,
    history: [],
    radarChart: null,
    trendChart: null
};

// DOM elements
const screens = {
    welcome: document.getElementById('screen-welcome'),
    survey: document.getElementById('screen-survey'),
    loading: document.getElementById('screen-loading'),
    result: document.getElementById('screen-result'),
    history: document.getElementById('screen-history')
};

// On document load
document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

function initApp() {
    // Unregister any legacy service workers from other projects (e.g. TreeDoctor) on localhost
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.getRegistrations().then(registrations => {
            for (const registration of registrations) {
                registration.unregister();
                console.log('[Self-Healing] Unregistered legacy service worker:', registration);
            }
        });
    }
    registerEventListeners();
    loadHistoryFromLocal();
    updateNavUI();
}

function registerEventListeners() {
    // Navigation
    document.getElementById('btn-nav-home').addEventListener('click', () => showScreen('screen-welcome'));
    document.getElementById('btn-nav-history').addEventListener('click', () => {
        showScreen('screen-history');
        renderHistoryTrendChart();
        renderHistoryList();
    });
    document.getElementById('btn-history-view').addEventListener('click', () => {
        showScreen('screen-history');
        renderHistoryTrendChart();
        renderHistoryList();
    });

    // Welcome Screen
    document.getElementById('btn-start').addEventListener('click', () => {
        resetWizard();
        showScreen('screen-survey');
    });

    // Wizard Navigation Buttons
    document.querySelectorAll('.btn-next').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const nextStep = parseInt(e.currentTarget.getAttribute('data-next'));
            if (validateStep(state.currentStep)) {
                goToStep(nextStep);
            }
        });
    });

    document.querySelectorAll('.btn-prev').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const prevStep = parseInt(e.currentTarget.getAttribute('data-prev'));
            goToStep(prevStep);
        });
    });


    // Toggle Guides functionality
    const btnToggleGuides = document.getElementById('btn-toggle-guides');
    if (btnToggleGuides) {
        btnToggleGuides.addEventListener('click', () => {
            const isHidden = btnToggleGuides.getAttribute('data-hidden') === 'true';
            const guideBoxes = document.querySelectorAll('.slot-guide-box');
            
            guideBoxes.forEach(box => {
                box.style.display = isHidden ? 'flex' : 'none';
            });
            
            if (isHidden) {
                btnToggleGuides.setAttribute('data-hidden', 'false');
                btnToggleGuides.innerHTML = '<i class="fa-solid fa-circle-xmark"></i> 촬영 가이드 접기';
                btnToggleGuides.classList.remove('btn-secondary');
                btnToggleGuides.classList.add('btn-primary');
            } else {
                btnToggleGuides.setAttribute('data-hidden', 'true');
                btnToggleGuides.innerHTML = '<i class="fa-solid fa-circle-info"></i> 촬영 가이드 보기';
                btnToggleGuides.classList.remove('btn-primary');
                btnToggleGuides.classList.add('btn-secondary');
            }
        });
    }

    // File Dropzone interaction (3 Zones)
    const slots = ['crown', 'front', 'back'];
    slots.forEach(slot => registerSlotEvents(slot));

    // Simulator slider updates
    const slidersMap = {
        redness: 'redness',
        'dead-skin': 'dead_skin',
        sebum: 'sebum',
        density: 'hair_density',
        thickness: 'hair_thickness'
    };
    
    const labels = {
        redness: ['0 (양호)', '1 (주의)', '2 (경고)', '3 (위험)'],
        'dead-skin': ['0 (양호)', '1 (주의)', '2 (경고)', '3 (위험)'],
        sebum: ['0 (건조/정상)', '1 (주의)', '2 (경고/과유분)', '3 (위험/개기름)'],
        density: ['0 (위험/탈모)', '1 (경고/희소)', '2 (주의/평범)', '3 (양호/풍성)'],
        thickness: ['0 (위험/연모화)', '1 (경고/가늘어짐)', '2 (주의/보통)', '3 (양호/굵음)']
    };
 
    Object.entries(slidersMap).forEach(([sliderId, stateKey]) => {
        const el = document.getElementById(`sim-${sliderId}`);
        if (el) {
            el.addEventListener('input', (e) => {
                const val = parseInt(e.target.value);
                state.visionScores[stateKey] = val;
                document.getElementById(`val-${sliderId}`).textContent = labels[sliderId][val];
            });
        }
    });

    // AI Vision analysis button click listener
    const btnRunVision = document.getElementById('btn-run-vision');
    if (btnRunVision) {
        btnRunVision.addEventListener('click', runVisionAnalysis);
    }

    // Final Report submission
    document.getElementById('btn-submit').addEventListener('click', startAnalysis);

    // PDF download
    document.getElementById('btn-download-pdf').addEventListener('click', () => {
        if (state.latestReport && state.latestReport.id) {
            window.open(`${API_BASE}/pdf/${state.latestReport.id}`, '_blank');
        }
    });

    // Restart button
    document.getElementById('btn-restart').addEventListener('click', () => {
        resetWizard();
        showScreen('screen-survey');
    });

    // Admin Center Link Cache Buster
    const adminLink = document.querySelector('.admin-link');
    if (adminLink) {
        adminLink.addEventListener('click', (e) => {
            e.preventDefault();
            // Force a cache-busting timestamp query parameter to bypass browser/service-worker caching of localhosts
            window.open(`admin.html?t=${Date.now()}`, '_blank');
        });
    }
}

function showScreen(screenId) {
    Object.keys(screens).forEach(key => {
        screens[key].classList.remove('active');
    });
    
    const target = document.getElementById(screenId);
    if (target) {
        target.classList.add('active');
        state.currentScreen = screenId;
    }
    
    updateNavUI();
}

function updateNavUI() {
    const navHome = document.getElementById('btn-nav-home');
    const navHistory = document.getElementById('btn-nav-history');

    navHome.classList.remove('active');
    navHistory.classList.remove('active');

    if (state.currentScreen === 'screen-welcome' || state.currentScreen === 'screen-survey') {
        navHome.classList.add('active');
    } else if (state.currentScreen === 'screen-history') {
        navHistory.classList.add('active');
    }
}

// Wizard state management
function resetWizard() {
    state.currentStep = 1;
    state.selectedFileCrown = null;
    state.selectedFileFront = null;
    state.selectedFileBack = null;
    state.isAiAnalyzed = false;
    
    const badgeAi = document.getElementById('badge-ai-status');
    if (badgeAi) badgeAi.style.display = 'none';
    const btnRunVision = document.getElementById('btn-run-vision');
    if (btnRunVision) btnRunVision.disabled = true;
    
    ['crown', 'front', 'back'].forEach(slot => {
        const fileInput = document.getElementById(`file-input-${slot}`);
        if (fileInput) fileInput.value = '';
        const previewContainer = document.getElementById(`preview-container-${slot}`);
        if (previewContainer) previewContainer.style.display = 'none';
        const dropzoneContent = document.querySelector(`#dropzone-${slot} .dropzone-content-mini`);
        if (dropzoneContent) dropzoneContent.style.display = 'flex';
    });
    
    // Clear survey selections
    document.getElementById('user-name').value = '박지성';
    document.getElementById('user-age').value = 28;
    document.querySelector('input[name="user-gender"][value="male"]').checked = true;
    document.getElementById('user-location').value = '서울시 강남구';
    document.querySelector('input[name="user-family"][value="paternal_side"]').checked = true;
    
    document.querySelectorAll('input[name="symptoms"]').forEach(chk => {
        chk.checked = false;
    });

    // Reset sliders
    const defaultVals = { redness: 1, dead_skin: 1, sebum: 2, hair_density: 2, hair_thickness: 2 };
    state.visionScores = { ...defaultVals };
    
    document.getElementById('sim-redness').value = 1;
    document.getElementById('sim-dead-skin').value = 1;
    document.getElementById('sim-sebum').value = 2;
    document.getElementById('sim-density').value = 2;
    document.getElementById('sim-thickness').value = 2;

    document.getElementById('val-redness').textContent = '1 (주의)';
    document.getElementById('val-dead-skin').textContent = '1 (주의)';
    document.getElementById('val-sebum').textContent = '2 (경고/과유분)';
    document.getElementById('val-density').textContent = '2 (주의/평범)';
    document.getElementById('val-thickness').textContent = '2 (주의/보통)';

    goToStep(1);
}

function goToStep(step) {
    document.querySelectorAll('.wizard-step').forEach(el => {
        el.classList.remove('active');
    });
    
    const targetStep = document.getElementById(`step-${step}`);
    if (targetStep) {
        targetStep.classList.add('active');
        state.currentStep = step;
        
        // Update progress bar
        document.querySelectorAll('.progress-step').forEach(el => {
            const s = parseInt(el.getAttribute('data-step'));
            el.classList.remove('active');
            if (s <= step) {
                el.classList.add('active');
            }
        });
    }
}

function validateStep(step) {
    if (step === 1) {
        const name = document.getElementById('user-name').value.trim();
        const age = parseInt(document.getElementById('user-age').value);
        const loc = document.getElementById('user-location').value.trim();
        if (!name) {
            alert('성함을 입력해 주세요.');
            return false;
        }
        if (isNaN(age) || age < 1 || age > 120) {
            alert('유효한 만 나이를 입력해 주세요.');
            return false;
        }
        if (!loc) {
            alert('거주지 또는 관심 지역을 입력해 주세요.');
            return false;
        }
    }
    return true;
}

function registerSlotEvents(slotName) {
    const dropzone = document.getElementById(`dropzone-${slotName}`);
    const fileInput = document.getElementById(`file-input-${slotName}`);
    const previewContainer = document.getElementById(`preview-container-${slotName}`);
    const removeBtn = document.getElementById(`btn-remove-${slotName}`);

    dropzone.addEventListener('click', (e) => {
        if (e.target !== removeBtn && !removeBtn.contains(e.target)) {
            fileInput.click();
        }
    });

    fileInput.addEventListener('change', (e) => {
        handleFileSelectionMini(e.target.files[0], slotName);
    });

    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragging');
    });

    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('dragging');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragging');
        handleFileSelectionMini(e.dataTransfer.files[0], slotName);
    });

    removeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.value = '';
        state[`selectedFile${slotName.charAt(0).toUpperCase() + slotName.slice(1)}`] = null;
        previewContainer.style.display = 'none';
        dropzone.querySelector('.dropzone-content-mini').style.display = 'flex';
        updateVisionButtonState();
    });
}

function handleFileSelectionMini(file, slotName) {
    if (!file) return;
    if (!file.type.startsWith('image/')) {
        alert('이미지 파일만 업로드할 수 있습니다.');
        return;
    }

    state[`selectedFile${slotName.charAt(0).toUpperCase() + slotName.slice(1)}`] = file;
    updateVisionButtonState();
    
    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById(`preview-${slotName}`).src = e.target.result;
        document.getElementById(`preview-container-${slotName}`).style.display = 'flex';
        document.querySelector(`#dropzone-${slotName} .dropzone-content-mini`).style.display = 'none';
    };
    reader.readAsDataURL(file);
}

function updateVisionButtonState() {
    const hasFiles = !!(state.selectedFileCrown || state.selectedFileFront || state.selectedFileBack);
    const btnRunVision = document.getElementById('btn-run-vision');
    if (btnRunVision) {
        btnRunVision.disabled = !hasFiles;
    }
    
    state.isAiAnalyzed = false;
    const badgeAi = document.getElementById('badge-ai-status');
    if (badgeAi) {
        badgeAi.style.display = 'none';
    }
}

async function runVisionAnalysis() {
    const hasFiles = !!(state.selectedFileCrown || state.selectedFileFront || state.selectedFileBack);
    if (!hasFiles) {
        alert('분석할 두피 사진을 최소 1장 이상 업로드해 주세요.');
        return;
    }

    const btnRunVision = document.getElementById('btn-run-vision');
    const btnSubmit = document.getElementById('btn-submit');
    const visionStatus = document.getElementById('vision-status');
    const visionStatusText = document.getElementById('vision-status-text');

    if (btnRunVision) btnRunVision.disabled = true;
    if (btnSubmit) btnSubmit.disabled = true;
    if (visionStatus) {
        visionStatus.style.display = 'flex';
        if (visionStatusText) visionStatusText.textContent = '비전 AI가 사진 분석을 통해 두피 상태를 대조 판독하는 중...';
    }

    try {
        const formData = new FormData();
        if (state.selectedFileCrown) formData.append('image_crown', state.selectedFileCrown);
        if (state.selectedFileFront) formData.append('image_front', state.selectedFileFront);
        if (state.selectedFileBack) formData.append('image_back', state.selectedFileBack);

        const response = await fetch(`${API_BASE}/analyze-images`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error('비전 AI 분석 요청에 실패했습니다.');
        }

        const data = await response.json();
        state.visionScores = data;
        state.isAiAnalyzed = true;

        // Update Slider UI values
        const slidersMap = {
            redness: 'redness',
            'dead-skin': 'dead_skin',
            sebum: 'sebum',
            density: 'hair_density',
            thickness: 'hair_thickness'
        };

        const labelsMap = {
            redness: ['0 (양호)', '1 (주의)', '2 (경고)', '3 (위험)'],
            'dead-skin': ['0 (양호)', '1 (주의)', '2 (경고)', '3 (위험)'],
            sebum: ['0 (건조/정상)', '1 (주의)', '2 (경고/과유분)', '3 (위험/개기름)'],
            density: ['0 (위험/탈모)', '1 (경고/희소)', '2 (주의/평범)', '3 (양호/풍성)'],
            thickness: ['0 (위험/연모화)', '1 (경고/가늘어짐)', '2 (주의/보통)', '3 (양호/굵음)']
        };

        Object.entries(slidersMap).forEach(([sliderId, stateKey]) => {
            const scoreVal = data[stateKey] !== undefined ? data[stateKey] : 1;
            const sliderEl = document.getElementById(`sim-${sliderId}`);
            const labelEl = document.getElementById(`val-${sliderId}`);
            
            if (sliderEl) {
                sliderEl.value = scoreVal;
            }
            if (labelEl) {
                labelEl.textContent = labelsMap[sliderId][scoreVal];
            }
            
            // Add animation highlight
            const sliderGroup = sliderEl ? sliderEl.closest('.slider-group') : null;
            if (sliderGroup) {
                sliderGroup.classList.remove('ai-highlighted');
                // trigger reflow
                void sliderGroup.offsetWidth;
                sliderGroup.classList.add('ai-highlighted');
                setTimeout(() => {
                    sliderGroup.classList.remove('ai-highlighted');
                }, 1800);
            }
        });

        // Show AI completion badge
        const badgeAi = document.getElementById('badge-ai-status');
        if (badgeAi) {
            badgeAi.style.display = 'inline-flex';
        }

    } catch (err) {
        alert(`AI 분석 오류: ${err.message}`);
    } finally {
        if (btnRunVision) btnRunVision.disabled = false;
        if (btnSubmit) btnSubmit.disabled = false;
        if (visionStatus) visionStatus.style.display = 'none';
    }
}

// Perform AI Scalp analysis
async function startAnalysis() {
    // 1. Gather profile and survey data
    state.profile.name = document.getElementById('user-name').value.trim() || '고객';
    state.profile.age = parseInt(document.getElementById('user-age').value);
    state.profile.gender = document.querySelector('input[name="user-gender"]:checked').value;
    state.profile.location = document.getElementById('user-location').value.trim();
    state.profile.family_history = document.querySelector('input[name="user-family"]:checked').value;

    state.symptoms = [];
    document.querySelectorAll('input[name="symptoms"]:checked').forEach(chk => {
        state.symptoms.push(chk.value);
    });

    showScreen('screen-loading');
    animateLoadingFill();

    try {
        let visionScores = { ...state.visionScores };

        // Checkpoint 1: Run Gemini Vision Analysis if image uploaded but not analyzed yet
        const hasUploadedImages = !!(state.selectedFileCrown || state.selectedFileFront || state.selectedFileBack);
        if (hasUploadedImages && !state.isAiAnalyzed) {
            updateLoadingStatus('status-1', 'active', '비전 AI가 3개 환부 사진 정밀 비교 판독 중...');
            
            const formData = new FormData();
            if (state.selectedFileCrown) formData.append('image_crown', state.selectedFileCrown);
            if (state.selectedFileFront) formData.append('image_front', state.selectedFileFront);
            if (state.selectedFileBack) formData.append('image_back', state.selectedFileBack);

            const vResp = await fetch(`${API_BASE}/analyze-images`, {
                method: 'POST',
                body: formData
            });

            if (!vResp.ok) {
                throw new Error('다중 환부 비전 AI 자동 분석에 실패했습니다.');
            }

            const vData = await vResp.json();
            visionScores = vData;
            state.visionScores = vData;
            state.isAiAnalyzed = true;
        }

        updateLoadingStatus('status-1', 'done', '<i class="fa-solid fa-circle-check"></i> 두피 비전 인자 판독 완료');
        updateLoadingStatus('status-2', 'active', '문진 데이터 교차 분석 중...');

        // Checkpoint 2: Call Wellness Report Diagnose Endpoint
        const diagnosePayload = {
            user_id: state.profile.name,
            vision_analysis: visionScores,
            user_survey: {
                age: state.profile.age,
                gender: state.profile.gender,
                family_history: state.profile.family_history,
                subjective_symptoms: state.symptoms
            },
            location: state.profile.location
        };

        const dResp = await fetch(`${API_BASE}/diagnose`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(diagnosePayload)
        });

        if (!dResp.ok) {
            throw new Error('AI 가이드 리포트 생성에 실패했습니다.');
        }

        updateLoadingStatus('status-2', 'done', '<i class="fa-solid fa-circle-check"></i> 문진 데이터 분석 완료');
        updateLoadingStatus('status-3', 'active', '식약처 인증 성분 솔루션 구성 완료');
        updateLoadingStatus('status-4', 'active', 'AI 안전성 검증 및 리포트 데이터 바인딩 중...');

        const reportData = await dResp.json();
        state.latestReport = reportData;

        // Fetch location-based partners
        let partners = [];
        try {
            const pResp = await fetch(`${API_BASE}/partners?location=${encodeURIComponent(state.profile.location)}`);
            if (pResp.ok) {
                partners = await pResp.json();
            }
        } catch (pe) {
            console.error('Failed to load local partners:', pe);
        }

        state.latestReport.partners = partners;

        // Save report to local history
        saveReportToLocal(reportData);

        // Display results
        setTimeout(() => {
            renderResultDashboard(reportData);
            showScreen('screen-result');
        }, 1200);

    } catch (err) {
        alert(`분석 오류 발생: ${err.message}`);
        showScreen('screen-survey');
    }
}

// Loading UI animations
function animateLoadingFill() {
    const bar = document.getElementById('loading-bar');
    bar.style.width = '0%';
    
    let progress = 0;
    const interval = setInterval(() => {
        if (progress >= 95) {
            clearInterval(interval);
        } else {
            progress += Math.random() * 8;
            bar.style.width = `${Math.min(95, progress)}%`;
        }
    }, 200);
}

function updateLoadingStatus(elementId, type, htmlText) {
    const el = document.getElementById(elementId);
    if (el) {
        el.innerHTML = htmlText;
        el.className = 'status-item';
        if (type === 'active') {
            el.classList.add('active');
        } else if (type === 'done') {
            el.classList.add('active');
            el.style.color = '#10b981';
        }
    }
}

// Results visualization rendering
function renderResultDashboard(report) {
    // 0. Update Custom Title with Fingerprint Concept
    const reportTitle = document.getElementById('report-title-label');
    if (reportTitle) {
        reportTitle.innerHTML = `<i class="fa-solid fa-fingerprint" style="color: #a78bfa; margin-right: 8px;"></i> ${report.user_id}님의 두피 지문 분석 및 전용 케어 제안서`;
    }

    // 1. Overall Score Gauge
    document.getElementById('res-score').textContent = report.overall_score;
    document.getElementById('res-grade').textContent = report.overall_grade;
    
    // Set circle dash offset
    const circle = document.getElementById('gauge-fill-circle');
    const radius = circle.r.baseVal.value;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (report.overall_score / 100) * circumference;
    circle.style.strokeDasharray = `${circumference}`;
    circle.style.strokeDashoffset = offset;
    
    // Set color matching severity
    if (report.overall_score < 50) {
        circle.style.stroke = '#ef4444'; // Red
    } else if (report.overall_score < 80) {
        circle.style.stroke = '#f59e0b'; // Yellow
    } else {
        circle.style.stroke = '#10b981'; // Green
    }

    // 2. Radar Chart Visualization
    const ctx = document.getElementById('radarChart').getContext('2d');
    if (state.radarChart) {
        state.radarChart.destroy();
    }

    const labels = ['홍반(붉은기)', '각질(비듬)', '피지(유분)', '모발 밀도', '모발 굵기'];
    const dataValues = [
        state.visionScores.redness,
        state.visionScores.dead_skin,
        state.visionScores.sebum,
        state.visionScores.hair_density,
        state.visionScores.hair_thickness
    ];

    state.radarChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: '내 두피 상태 (0~3)',
                    data: dataValues,
                    backgroundColor: 'rgba(139, 92, 246, 0.25)',
                    borderColor: '#8b5cf6',
                    borderWidth: 2,
                    pointBackgroundColor: '#a78bfa',
                    pointBorderColor: '#fff',
                    pointRadius: 4
                },
                {
                    label: '정상 두피 기준',
                    data: [0, 0, 0, 3, 3], // Ideal standard: redness 0, dead_skin 0, sebum 0, density 3, thickness 3
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderColor: '#10b981',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    pointBackgroundColor: '#34d399',
                    pointBorderColor: '#fff',
                    pointRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    angleLines: { color: 'rgba(255, 255, 255, 0.1)' },
                    grid: { color: 'rgba(255, 255, 255, 0.08)' },
                    pointLabels: { color: '#9ca3af', font: { family: 'Inter', size: 11 } },
                    ticks: { display: false, stepSize: 1 },
                    min: 0,
                    max: 3
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: '#e5e7eb',
                        font: { family: 'Inter', size: 10 }
                    }
                }
            }
        }
    });

    // 3. AI opinion and solutions Text format
    document.getElementById('res-opinion').innerHTML = parseMarkdown(report.ai_opinion);
    document.getElementById('res-solution').innerHTML = parseMarkdown(report.homecare_solution);

    // 4. Partner Centers List matching
    const partnersBox = document.getElementById('res-partners');
    partnersBox.innerHTML = '';
    
    if (report.partners && report.partners.length > 0) {
        report.partners.forEach(p => {
            const card = document.createElement('div');
            card.className = 'partner-card';
            card.innerHTML = `
                <div class="partner-header">
                    <span class="partner-name">${p.name}</span>
                    <span class="partner-cat">${p.category}</span>
                </div>
                <div class="partner-detail">
                    <span><i class="fa-solid fa-location-dot"></i> ${p.address}</span>
                    <span><i class="fa-solid fa-phone"></i> ${p.phone}</span>
                </div>
                <div class="partner-benefit">
                    <i class="fa-solid fa-gift"></i> 제휴혜택: ${p.benefit}
                </div>
            `;
            partnersBox.appendChild(card);
        });
    } else {
        partnersBox.innerHTML = `
            <div class="no-history">
                <i class="fa-solid fa-location-crosshairs"></i>
                <p>해당 지역 인근에 제휴 파트너가 없습니다. 전국 지점 가이드를 참고하세요.</p>
            </div>
        `;
    }
}

// LocalStorage History Sync & Self-Healing
function saveReportToLocal(report) {
    const list = JSON.parse(localStorage.getItem('scalp_history') || '[]');
    // Avoid duplicates
    if (!list.some(item => item.id === report.id)) {
        list.push({
            id: report.id,
            user_id: report.user_id, // Save user name in history to prevent undefined name on restore
            overall_score: report.overall_score,
            overall_grade: report.overall_grade,
            redness: state.visionScores.redness,
            dead_skin: state.visionScores.dead_skin,
            sebum: state.visionScores.sebum,
            hair_density: state.visionScores.hair_density,
            hair_thickness: state.visionScores.hair_thickness,
            created_at: new Date().toLocaleDateString('ko-KR')
        });
    }
    localStorage.setItem('scalp_history', JSON.stringify(list));
    state.history = list;
}

function loadHistoryFromLocal() {
    state.history = JSON.parse(localStorage.getItem('scalp_history') || '[]');
}

// Render Timeline Progress Chart
function renderHistoryTrendChart() {
    const ctx = document.getElementById('trendChart').getContext('2d');
    if (state.trendChart) {
        state.trendChart.destroy();
    }

    if (state.history.length === 0) {
        return;
    }

    // Sort chronologically
    const sortedHistory = [...state.history].reverse();
    const dates = sortedHistory.map(h => h.created_at);
    const scores = sortedHistory.map(h => h.overall_score);

    state.trendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                label: '종합 웰니스 점수',
                data: scores,
                borderColor: '#a78bfa',
                backgroundColor: 'rgba(139, 92, 246, 0.1)',
                borderWidth: 3,
                tension: 0.35,
                fill: true,
                pointBackgroundColor: '#8b5cf6',
                pointRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#9ca3af' }
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

// Render previous history item lists
function renderHistoryList() {
    const listContainer = document.getElementById('history-items-list');
    listContainer.innerHTML = '';

    if (state.history.length === 0) {
        listContainer.innerHTML = `
            <div class="no-history">
                <i class="fa-solid fa-folder-open"></i>
                <p>저장된 분석 이력이 존재하지 않습니다. 먼저 첫 검사를 진행하세요!</p>
            </div>
        `;
        return;
    }

    state.history.forEach(h => {
        const card = document.createElement('div');
        card.className = 'history-item-card';
        card.innerHTML = `
            <div class="history-item-left">
                <span class="history-item-date">${h.created_at}</span>
                <span class="history-item-title">${h.overall_grade}</span>
                <span class="history-item-metrics">홍반: ${h.redness} | 각질: ${h.dead_skin} | 피지: ${h.sebum} | 밀도: ${h.hair_density} | 굵기: ${h.hair_thickness}</span>
            </div>
            <div class="history-item-right">
                <span class="history-item-score">${h.overall_score}점</span>
                <i class="fa-solid fa-chevron-right text-muted"></i>
            </div>
        `;
        
        card.addEventListener('click', () => loadHistoricalReport(h.id));
        listContainer.appendChild(card);
    });
}

// Load past report from Server DB or LocalStorage Backup (Self Healing)
async function loadHistoricalReport(reportId) {
    showScreen('screen-loading');
    animateLoadingFill();

    try {
        const resp = await fetch(`${API_BASE}/report/${reportId}`);
        if (!resp.ok) {
            // Self-Healing Trigger: If server database is deleted but client has localized cache,
            // we restore the record back to server and load it seamlessly.
            const localRecord = state.history.find(h => h.id === reportId);
            if (localRecord) {
                console.warn('[Self-Healing] Report not on server, restoring from localStorage cache...');
                
                const restorePayload = {
                    user_id: localRecord.user_id || state.profile.name || 'default_user',
                    vision_analysis: {
                        redness: localRecord.redness,
                        dead_skin: localRecord.dead_skin,
                        sebum: localRecord.sebum,
                        hair_density: localRecord.hair_density,
                        hair_thickness: localRecord.hair_thickness
                    },
                    user_survey: {
                        age: state.profile.age,
                        gender: state.profile.gender,
                        family_history: state.profile.family_history,
                        subjective_symptoms: state.symptoms
                    },
                    location: state.profile.location
                };

                const restoreResp = await fetch(`${API_BASE}/diagnose`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(restorePayload)
                });
                
                if (restoreResp.ok) {
                    const restoredData = await restoreResp.json();
                    state.latestReport = restoredData;
                    state.visionScores = {
                        redness: localRecord.redness,
                        dead_skin: localRecord.dead_skin,
                        sebum: localRecord.sebum,
                        hair_density: localRecord.hair_density,
                        hair_thickness: localRecord.hair_thickness
                    };
                    renderResultDashboard(restoredData);
                    showScreen('screen-result');
                    return;
                }
            }
            throw new Error('이력 리포트를 가져오지 못했습니다.');
        }

        const report = await resp.json();
        state.latestReport = report;
        state.visionScores = {
            redness: report.redness,
            dead_skin: report.dead_skin,
            sebum: report.sebum,
            hair_density: report.hair_density,
            hair_thickness: report.hair_thickness
        };

        // Fetch location-based partners for history view
        let partners = [];
        try {
            const pResp = await fetch(`${API_BASE}/partners?location=${encodeURIComponent(report.location)}`);
            if (pResp.ok) {
                partners = await pResp.json();
            }
        } catch (pe) {
            console.error('Failed to load local partners for history view:', pe);
        }
        state.latestReport.partners = partners;

        renderResultDashboard(report);
        showScreen('screen-result');

    } catch (err) {
        alert(err.message);
        showScreen('screen-history');
    }
}

// Markdown parser helper for visual formatting of LLM reports
function parseMarkdown(text) {
    if (!text) return '';
    
    const lines = text.split('\n');
    let html = '';
    let inList = false;
    let inStepCard = false;
    
    lines.forEach(line => {
        let cleanLine = line.trim();
        if (!cleanLine) return;
        
        // Remove redundant section headers (e.g. ### 초개인화 홈케어 솔루션)
        if (cleanLine.match(/^(#+\s*|###\s*|####\s*)(초개인화 홈케어 솔루션|AI 종합 가이드 분석 의견|AI 맞춤형 종합 가이드 분석 의견|전문가 웰니스 검사 제안.*|종합 의견)\s*$/i)) {
            return;
        }

        // Convert subheaders
        if (cleanLine.startsWith('### ')) {
            if (inList) { html += '</ul>'; inList = false; }
            if (inStepCard) { html += '</div>'; inStepCard = false; }
            const headerText = cleanLine.replace(/^###\s+/, '');
            html += `<h5 class="markdown-h3">${parseInlineMarkdown(headerText)}</h5>`;
            return;
        }
        if (cleanLine.startsWith('#### ')) {
            if (inList) { html += '</ul>'; inList = false; }
            if (inStepCard) { html += '</div>'; inStepCard = false; }
            const headerText = cleanLine.replace(/^####\s+/, '');
            html += `<h6 class="markdown-h4">${parseInlineMarkdown(headerText)}</h6>`;
            return;
        }

        // Check if list item (starts with -, *, ✓, •, or 1.)
        const listRegex = /^([\-\*\u2713\u2022\u2714]|\d+\.)\s*(.*)$/;
        const match = cleanLine.match(listRegex);
        
        if (match) {
            const content = match[2].trim();
            
            // Check if this list item is a "Step Header" (contains "X단계: " or "X단계 ")
            const stepMatch = content.match(/^(\d+단계)\s*:\s*(.*)$/);
            if (stepMatch) {
                // Close previous list and card
                if (inList) { html += '</ul>'; inList = false; }
                if (inStepCard) { html += '</div>'; }
                
                inStepCard = true;
                const stepNum = stepMatch[1];
                const stepTitle = stepMatch[2];
                html += `
                <div class="step-card">
                    <div class="step-card-header">
                        <span class="step-badge">${stepNum}</span>
                        <span class="step-card-title">${parseInlineMarkdown(stepTitle)}</span>
                    </div>
                `;
            } else if (inStepCard) {
                // Inside a step card
                if (!inList) {
                    html += '<ul class="step-details-list">';
                    inList = true;
                }
                html += `<li>${parseInlineMarkdown(content)}</li>`;
            } else {
                // Standard list outside step card
                if (!inList) {
                    html += '<ul class="markdown-list">';
                    inList = true;
                }
                html += `<li>${parseInlineMarkdown(content)}</li>`;
            }
        } else {
            // Standard paragraph
            if (inList) { html += '</ul>'; inList = false; }
            if (inStepCard && !cleanLine.includes('단계')) {
                // Keep paragraph inside step card if it looks like details
                html += `<p class="markdown-p">${parseInlineMarkdown(cleanLine)}</p>`;
            } else {
                if (inStepCard) { html += '</div>'; inStepCard = false; }
                html += `<p class="markdown-p">${parseInlineMarkdown(cleanLine)}</p>`;
            }
        }
    });
    
    if (inList) { html += '</ul>'; }
    if (inStepCard) { html += '</div>'; }
    
    return html;
}

function parseInlineMarkdown(text) {
    if (!text) return '';
    
    // Parse bold syntax **text** -> <strong>text</strong>
    let parsed = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Handle unclosed bold markers at the end of the line
    parsed = parsed.replace(/\*\*(.*?)$/g, '<strong>$1</strong>');
    
    // Clean up remaining double asterisks
    parsed = parsed.replace(/\*\*/g, '');
    
    // Auto-bold category prefixes (e.g., "세정 방법: 미온수로..." -> "<strong>세정 방법:</strong> 미온수로...")
    if (!parsed.includes('<strong>') && parsed.includes(':')) {
        const parts = parsed.split(':');
        if (parts[0].length < 25) {
            const prefix = parts.shift();
            parsed = `<strong>${prefix}:</strong>${parts.join(':')}`;
        }
    }
    
    return parsed;
}
