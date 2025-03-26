// Daha önce gönderilen bildirimleri localStorage’dan al
let sentNotifications = JSON.parse(localStorage.getItem('sentNotifications')) || [];

// Fiyatları güncelleyen fonksiyon
function updatePrices() {
    fetch('/prices/json/')  // Fiyatları JSON formatında çeken endpoint
        .then(response => response.json())
        .then(data => {
            const tbody = document.getElementById('priceTableBody');
            const pairsToNotify = []; // Bildirim gönderilecek çiftler

            tbody.querySelectorAll('tr').forEach(row => {
                const pair = row.getAttribute('data-pair');
                const newPrice = data[pair];
                if (newPrice) {
                    const priceCell = row.querySelector('.current-price');
                    const oldPrice = parseFloat(priceCell.textContent);
                    priceCell.textContent = newPrice;
                    // Fiyat değişimine göre renk animasyonu
                    if (oldPrice < newPrice) {
                        priceCell.style.color = '#00ff00'; // Yeşil: Yükseliş
                    } else if (oldPrice > newPrice) {
                        priceCell.style.color = '#ff0000'; // Kırmızı: Düşüş
                    }
                    setTimeout(() => priceCell.style.color = '#e0e0e0', 1000); // 1 sn sonra normale dön
                }

                // Yükselme ihtimalini kontrol et ve bildirim gönder
                const riseCell = row.querySelector('.uptrend-cell');
                const riseProbability = parseInt(riseCell.getAttribute('data-rise'));
                if (riseProbability >= 51 && !sentNotifications.includes(pair)) {
                    pairsToNotify.push(pair);
                    sentNotifications.push(pair); // Bildirilen çifti kaydet
                }
            });

            // Bildirimleri gönder
            if (pairsToNotify.length > 0) {
                fetch('/send_notifications/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value // Django CSRF token
                    },
                    body: JSON.stringify({chat_id: '1001423950701', pairs: pairsToNotify})
                })
                .then(response => {
                    console.log('Bildirim gönderildi:', pairsToNotify);
                    localStorage.setItem('sentNotifications', JSON.stringify(sentNotifications));
                })
                .catch(error => console.error('Bildirim gönderilemedi:', error));
            }

            updateUptrendColors(); // Yükselme ihtimali renklerini güncelle
            updateDowntrendColors(); // Düşme ihtimali renklerini güncelle
        })
        .catch(error => console.error('Fiyatlar güncellenirken hata oluştu:', error));
}

// Diğer verileri güncelleyen fonksiyon (5 dakikada bir çalışacak)
function updateIndicators() {
    fetch('/indicators/json/')  // Göstergeleri JSON formatında çeken endpoint
        .then(response => response.json())
        .then(data => {
            const tbody = document.getElementById('priceTableBody');
            tbody.querySelectorAll('tr').forEach(row => {
                const pair = row.getAttribute('data-pair');
                const indicators = data[pair];
                if (indicators) {
                    // SMA Signal güncelle
                    const smaSignalCell = row.querySelector('.signal-cell');
                    smaSignalCell.textContent = indicators.sma_signal;
                    // Stoch Signal güncelle
                    const stochSignalCell = row.querySelector('.stoch-signal-cell');
                    stochSignalCell.textContent = indicators.stoch_signal;
                    // ADX güncelle
                    const adxCell = row.querySelector('td:nth-child(5)'); // ADX sütunu
                    adxCell.textContent = indicators.adx;
                    // ADX Signal güncelle
                    const adxSignalCell = row.querySelector('.adx-signal-cell');
                    adxSignalCell.textContent = indicators.adx_signal;
                    // RSI güncelle
                    const rsiCell = row.querySelector('td:nth-child(7)'); // RSI sütunu
                    rsiCell.textContent = indicators.rsi;
                    // RSI Signal güncelle
                    const rsiSignalCell = row.querySelector('.rsi-signal-cell');
                    rsiSignalCell.textContent = indicators.rsi_signal;
                    // Ichimoku Signal güncelle
                    const ichimokuSignalCell = row.querySelector('.ichimoku-signal-cell');
                    ichimokuSignalCell.textContent = indicators.ichimoku_signal;
                    // ATR güncelle
                    const atrCell = row.querySelector('td:nth-child(10)'); // ATR sütunu
                    atrCell.textContent = indicators.atr;
                    // ATR Signal güncelle
                    const atrSignalCell = row.querySelector('.atr-signal-cell');
                    atrSignalCell.textContent = indicators.atr_signal;
                    // VWAP güncelle
                    const vwapCell = row.querySelector('td:nth-child(12)'); // VWAP sütunu
                    vwapCell.textContent = indicators.vwap;
                    // VWAP Signal güncelle
                    const vwapSignalCell = row.querySelector('.vwap-signal-cell');
                    vwapSignalCell.textContent = indicators.vwap_signal;
                    // Near Fibo güncelle
                    const nearFiboCell = row.querySelector('td:nth-child(14)'); // Near Fibo sütunu
                    nearFiboCell.textContent = indicators.near_fibo;
                    // Reversal % güncelle
                    const reversalCell = row.querySelector('td:nth-child(15)'); // Reversal % sütunu
                    reversalCell.textContent = indicators.reversal;
                    // Downtrend % güncelle
                    const downtrendCell = row.querySelector('.downtrend-cell');
                    downtrendCell.textContent = indicators.downtrend;
                    downtrendCell.setAttribute('data-fall', indicators.downtrend);
                    // Uptrend % güncelle
                    const uptrendCell = row.querySelector('.uptrend-cell');
                    uptrendCell.textContent = indicators.uptrend;
                    uptrendCell.setAttribute('data-rise', indicators.uptrend);
                }
            });

            // Güncellenen verilere göre sinyal oklarını ve renkleri yenile
            updateStochSignals();
            updateRsiSignals();
            updateSignalArrows();
            updateAdxSignals();
            updateIchimokuSignals();
            updateAtrSignals();
            updateVwapSignals();
            updateUptrendColors();
            updateDowntrendColors();
        })
        .catch(error => console.error('Gösterge verileri güncellenirken hata oluştu:', error));
}

// Yükselme ihtimali hücrelerinin renklerini güncelle
function updateUptrendColors() {
    document.querySelectorAll('.uptrend-cell').forEach(cell => {
        const riseProbability = parseInt(cell.getAttribute('data-rise'));
        if (riseProbability > 50) {
            cell.classList.add('uptrend-high');
            cell.classList.remove('uptrend-low');
        } else {
            cell.classList.add('uptrend-low');
            cell.classList.remove('uptrend-high');
        }
    });
}

// Düşme ihtimali hücrelerinin renklerini güncelle
function updateDowntrendColors() {
    document.querySelectorAll('.downtrend-cell').forEach(cell => {
        const fallProbability = parseInt(cell.getAttribute('data-fall'));
        if (fallProbability > 50) {
            cell.classList.add('downtrend-high');
            cell.classList.remove('downtrend-low');
        } else {
            cell.classList.add('downtrend-low');
            cell.classList.remove('downtrend-high');
        }
    });
}

// Stochastic sinyallerini güncelle (oklarla göster)
function updateStochSignals() {
    document.querySelectorAll('.stoch-signal-cell').forEach(cell => {
        const signal = cell.textContent.trim();
        cell.innerHTML = '';
        if (signal === 'Alım') {
            cell.innerHTML = '<span class="stoch-buy-arrow">↑</span>';
        } else if (signal === 'Satış') {
            cell.innerHTML = '<span class="stoch-sell-arrow">↓</span>';
        } else if (signal === 'Nötr') {
            cell.innerHTML = '<span class="stoch-neutral">—</span>';
        } else {
            cell.innerHTML = signal;
        }
    });
}

// RSI sinyallerini güncelle (oklarla göster)
function updateRsiSignals() {
    document.querySelectorAll('.rsi-signal-cell').forEach(cell => {
        const signal = cell.textContent.trim();
        cell.innerHTML = '';
        if (signal === 'Aşırı Satım (Alım)') {
            cell.innerHTML = '<span class="rsi-buy-arrow">↑</span>';
        } else if (signal === 'Aşırı Alım (Satış)') {
            cell.innerHTML = '<span class="rsi-sell-arrow">↓</span>';
        } else if (signal === 'Nötr') {
            cell.innerHTML = '<span class="rsi-neutral">—</span>';
        } else {
            cell.innerHTML = signal;
        }
    });
}

// SMA sinyallerini güncelle (oklarla göster)
function updateSignalArrows() {
    document.querySelectorAll('.signal-cell').forEach(cell => {
        const signal = cell.textContent.trim();
        cell.innerHTML = '';
        if (signal === 'Golden Cross (Alım)') {
            cell.innerHTML = '<span class="golden-cross">↑</span>';
        } else if (signal === 'Death Cross (Satış)') {
            cell.innerHTML = '<span class="death-cross">↓</span>';
        } else {
            cell.innerHTML = signal;
        }
    });
}

// ADX sinyallerini güncelle (oklarla göster)
function updateAdxSignals() {
    document.querySelectorAll('.adx-signal-cell').forEach(cell => {
        const signal = cell.textContent.trim();
        cell.innerHTML = '';
        if (signal === 'Güçlü Yükseliş') {
            cell.innerHTML = '<span class="strong-up">↑</span>';
        } else if (signal === 'Güçlü Düşüş') {
            cell.innerHTML = '<span class="strong-down">↓</span>';
        } else if (signal === 'Zayıf Trend') {
            cell.innerHTML = '<span class="weak">—</span>';
        } else {
            cell.innerHTML = signal;
        }
    });
}

// Ichimoku sinyallerini güncelle (oklarla göster)
function updateIchimokuSignals() {
    document.querySelectorAll('.ichimoku-signal-cell').forEach(cell => {
        const signal = cell.textContent.trim();
        cell.innerHTML = '';
        if (signal === 'Yükseliş Trendi') {
            cell.innerHTML = '<span class="ichimoku-up">↑</span>';
        } else if (signal === 'Düşüş Trendi') {
            cell.innerHTML = '<span class="ichimoku-down">↓</span>';
        } else {
            cell.innerHTML = signal;
        }
    });
}

// ATR sinyallerini güncelle (oklarla göster)
function updateAtrSignals() {
    document.querySelectorAll('.atr-signal-cell').forEach(cell => {
        const signal = cell.textContent.trim();
        cell.innerHTML = '';
        if (signal === 'Yüksek Volatilite') {
            cell.innerHTML = '<span class="atr-high">↓</span>';
        } else {
            cell.innerHTML = signal;
        }
    });
}

// VWAP sinyallerini güncelle (oklarla göster)
function updateVwapSignals() {
    document.querySelectorAll('.vwap-signal-cell').forEach(cell => {
        const signal = cell.textContent.trim();
        cell.innerHTML = '';
        if (signal === 'Fiyat Ortalamanın Üzerinde') {
            cell.innerHTML = '<span class="vwap-up">↑</span>';
        } else if (signal === 'Fiyat Ortalamanın Altında') {
            cell.innerHTML = '<span class="vwap-down">↓</span>';
        } else {
            cell.innerHTML = signal;
        }
    });
}

// Tooltip işlemleri: Fare üzerine gelindiğinde açıklama göster
document.querySelectorAll('[data-tooltip]').forEach(element => {
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = element.getAttribute('data-tooltip');
    document.body.appendChild(tooltip);

    element.addEventListener('mouseover', (e) => {
        const rect = element.getBoundingClientRect();
        tooltip.style.top = (rect.top - tooltip.offsetHeight - 5) + 'px';
        tooltip.style.left = (rect.left + rect.width / 2 - tooltip.offsetWidth / 2) + 'px';
        tooltip.style.display = 'block';
    });

    element.addEventListener('mouseout', () => {
        tooltip.style.display = 'none';
    });
});

// Her 10 saniyede bir fiyatları güncelle
setInterval(updatePrices, 10000);

// Her 5 dakikada bir (300000 ms) diğer verileri güncelle
setInterval(updateIndicators, 300000);

// Sayfa yüklendiğinde ilk güncellemeleri yap
updatePrices();
updateIndicators();
updateUptrendColors();
updateDowntrendColors();
updateStochSignals();
updateRsiSignals();
updateSignalArrows();
updateAdxSignals();
updateIchimokuSignals();
updateAtrSignals();
updateVwapSignals();