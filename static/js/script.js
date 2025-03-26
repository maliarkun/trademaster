let sentNotifications = JSON.parse(localStorage.getItem('sentNotifications')) || [];

function updatePrices() {
    fetch('/prices/json/')
        .then(response => response.json())
        .then(data => {
            const tbody = document.getElementById('priceTableBody');
            const pairsToNotify = [];
            tbody.querySelectorAll('tr').forEach(row => {
                const pair = row.getAttribute('data-pair');
                const newPrice = data[pair];
                if (newPrice) {
                    const priceCell = row.querySelector('.current-price');
                    const oldPrice = parseFloat(priceCell.textContent);
                    priceCell.textContent = newPrice;
                    if (oldPrice < newPrice) {
                        priceCell.style.color = '#00ff00';
                    } else if (oldPrice > newPrice) {
                        priceCell.style.color = '#ff0000';
                    }
                    setTimeout(() => priceCell.style.color = '#e0e0e0', 1000);
                }
                const riseCell = row.querySelector('.uptrend-cell');
                const riseProbability = parseInt(riseCell.getAttribute('data-rise'));
                if (riseProbability >= 51 && !sentNotifications.includes(pair)) {
                    pairsToNotify.push(pair);
                    sentNotifications.push(pair);
                }
            });
            if (pairsToNotify.length > 0) {
                fetch('/send_notifications/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    },
                    body: JSON.stringify({chat_id: '1001423950701', pairs: pairsToNotify})
                })
                .then(response => {
                    console.log('Bildirim gönderildi:', pairsToNotify);
                    localStorage.setItem('sentNotifications', JSON.stringify(sentNotifications));
                })
                .catch(error => console.error('Bildirim gönderilemedi:', error));
            }
            updateUptrendColors();
            updateDowntrendColors();
        })
        .catch(error => console.error('Fiyatlar güncellenirken hata oluştu:', error));
}

function updateIndicators() {
    fetch('/indicators/json/')
        .then(response => response.json())
        .then(data => {
            const tbody = document.getElementById('priceTableBody');
            tbody.querySelectorAll('tr').forEach(row => {
                const pair = row.getAttribute('data-pair');
                const indicators = data[pair];
                if (indicators) {
                    row.querySelector('.signal-cell').textContent = indicators.sma_signal;
                    row.querySelector('.stoch-signal-cell').textContent = indicators.stoch_signal;
                    row.querySelector('td:nth-child(5)').textContent = indicators.adx;
                    row.querySelector('.adx-signal-cell').textContent = indicators.adx_signal;
                    row.querySelector('td:nth-child(7)').textContent = indicators.rsi;
                    row.querySelector('.rsi-signal-cell').textContent = indicators.rsi_signal;
                    row.querySelector('.ichimoku-signal-cell').textContent = indicators.ichimoku_signal;
                    row.querySelector('td:nth-child(10)').textContent = indicators.atr;
                    row.querySelector('.atr-signal-cell').textContent = indicators.atr_signal;
                    row.querySelector('td:nth-child(12)').textContent = indicators.vwap;
                    row.querySelector('.vwap-signal-cell').textContent = indicators.vwap_signal;
                    row.querySelector('td:nth-child(14)').textContent = indicators.near_fibo;
                    row.querySelector('td:nth-child(15)').textContent = indicators.reversal;
                    const downtrendCell = row.querySelector('.downtrend-cell');
                    downtrendCell.textContent = indicators.downtrend;
                    downtrendCell.setAttribute('data-fall', indicators.downtrend);
                    const uptrendCell = row.querySelector('.uptrend-cell');
                    uptrendCell.textContent = indicators.uptrend;
                    uptrendCell.setAttribute('data-rise', indicators.uptrend);
                }
            });
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

setInterval(updatePrices, 10000);
setInterval(updateIndicators, 300000);

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