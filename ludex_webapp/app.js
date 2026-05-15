// Telegram WebApp initialization
const tg = window.Telegram.WebApp;
tg.expand();
tg.ready();

// Get user data
let user = null;
if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
    user = tg.initDataUnsafe.user;
    document.getElementById('userName').innerText = user.first_name || 'Player';
    document.getElementById('userId').innerText = '@' + (user.username || 'guest');
} else {
    document.getElementById('userName').innerText = 'Guest';
    document.getElementById('userId').innerText = 'Login to play';
}

// ========== BACKEND API CONFIGURATION ==========
// IMPORTANT: Replace with your actual backend URL (ngrok or deployed server)
// For local testing with ngrok: "https://your-ngrok-id.ngrok.io"
const API_BASE = "https://hatchery-film-sworn.ngrok-free.dev";  // <-- CHANGE THIS
// If your bot is running locally with ngrok, put the ngrok URL here.
// If you don't have backend yet, the app will work in "demo mode" with local balance.

let currentBalance = 0;
let demoMode = false;  // becomes true if API fails

// Fetch real balance from your Python backend
async function fetchBalance() {
    if (!user || !user.id) return;
    try {
        const response = await fetch(`${API_BASE}/api/balance?user_id=${user.id}`, {
            headers: {
                'ngrok-skip-browser-warning': 'true'
            }
        });
        if (!response.ok) throw new Error();
        const data = await response.json();
        currentBalance = data.balance;
        document.getElementById('balance').innerText = currentBalance;
        demoMode = false;
    } catch (error) {
        console.warn("Backend not reachable – using demo mode", error);
        demoMode = true;
        if (currentBalance === 0) currentBalance = 100;
        document.getElementById('balance').innerText = currentBalance;
    }
}

// Update balance on UI after a game
function updateBalanceUI(newBalance) {
    currentBalance = newBalance;
    document.getElementById('balance').innerText = currentBalance;
}

// Send game result to backend
async function submitGameResult(userId, bet, won) {
    if (demoMode) {
        // ... demo logic ...
    }
    try {
        const res = await fetch(`${API_BASE}/api/game/result`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'ngrok-skip-browser-warning': 'true'
            },
            body: JSON.stringify({ user_id: userId, bet: bet, won: won })
        });
        const data = await res.json();
        if (data.new_balance !== undefined) {
            updateBalanceUI(data.new_balance);
        }
        return data;
    } catch (err) {
        console.error("Backend error", err);
        return null;
    }
}
// ========== MODAL MANAGEMENT ==========
const modal = document.getElementById('gameModal');
const modalTitle = document.getElementById('modalTitle');
const modalBody = document.getElementById('modalBody');

function openModal(title, contentHtml) {
    modalTitle.innerText = title;
    modalBody.innerHTML = contentHtml;
    modal.style.display = 'flex';
    // Attach event listeners after content is inserted
    if (title === 'Card Flip') {
        attachCardFlipEvents();
    }
}

function closeModal() {
    modal.style.display = 'none';
}

document.querySelector('.close-modal').addEventListener('click', closeModal);
window.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
});

// ========== GAMES ==========
// Card Flip Game HTML
function getCardFlipHTML() {
    return `
        <div class="cardflip-game">
            <p>💎 Find the hidden diamond to win! 10% fee on wins.</p>
            <div class="cards-container">
                <div class="flip-card" data-index="0">?</div>
                <div class="flip-card" data-index="1">?</div>
                <div class="flip-card" data-index="2">?</div>
            </div>
             <input type="number" id="betAmount" class="bet-input" placeholder="Bet amount (Min 1 Birr)" min="1" value="10">
            <button id="playCardFlipBtn" class="game-action-btn">🎲 PLAY</button>
            <div id="gameResultMsg" class="game-result"></div>
        </div>
    `;
}

function attachCardFlipEvents() {
    let gameActive = true;
    const cards = document.querySelectorAll('.flip-card');
    const playBtn = document.getElementById('playCardFlipBtn');
    const betInput = document.getElementById('betAmount');
    const resultDiv = document.getElementById('gameResultMsg');
    
    if (!cards.length) return;
    
    async function handleFlip(cardElement, chosenIndex) {
        if (!gameActive) {
            resultDiv.innerHTML = "⚠️ Game already played. Close and reopen to play again.";
            return;
        } 

          const bet = parseInt(betInput.value);
        if (isNaN(bet) || bet < 1) {
            resultDiv.innerHTML = "❌ Enter a valid bet amount (≥1 Birr)";
            return;
        }
        if (bet > currentBalance) {
            resultDiv.innerHTML = "❌ Insufficient balance! You have ${currentBalance} Birr.";
            return;
        }

            // Random winning card (0,1,2)
        const winningIndex = Math.floor(Math.random() * 3);
        
        // Reveal all cards
        cards.forEach((c, i) => {
            if (i === winningIndex) c.innerHTML = "💎";
            else c.innerHTML = "❌";
            c.style.pointerEvents = "none";
        });

         const won = (chosenIndex === winningIndex);
        let message = "";
        
        // Send result to backend
        const result = await submitGameResult(user?.id, bet, won);
        
        if (won) {
            const winAmount = result?.won || Math.floor(bet * 0.9);
            message = "✅ YOU WON! +${winAmount} Birr (${bet} bet - 10% fee)";
            resultDiv.style.color = "#00ff88";
        } else {
            message = "❌ YOU LOST! -${bet} Birr";
            resultDiv.style.color = "#ff4757";
        }
        resultDiv.innerHTML = message;
        gameActive = false;
    }

     // Add click listeners to cards
    cards.forEach((card, idx) => {
        const newCard = card.cloneNode(true);
        card.parentNode.replaceChild(newCard, card);
        newCard.addEventListener('click', () => handleFlip(newCard, idx));
    });
    
    // Play button also triggers? Actually we want card click to trigger, but we keep play button as reset?
    if (playBtn) {
        playBtn.removeEventListener('click', playBtn._listener);
        playBtn._listener = () => {
            if (!gameActive) {
                resultDiv.innerHTML = "🔄 Game already finished. Close and reopen to start fresh.";
            } else {
                resultDiv.innerHTML = "🃏 Click on a card to flip!";
            }
        };
        playBtn.addEventListener('click', playBtn._listener);
    }
}


// ========== GAME SELECTION HANDLER ==========
document.querySelectorAll('.game-card').forEach(card => {
    card.addEventListener('click', () => {
        const game = card.getAttribute('data-game');
        switch(game) {
            case 'cardflip':
                openModal('Card Flip', getCardFlipHTML());
                break;
            case 'ludo':
                openModal('Ludo', '<p style="text-align:center">🎲 Ludo coming soon! Multiplayer mode in development.</p>');
                break;
            case 'bingo':
                openModal('Bingo', '<p style="text-align:center">🎯 Bingo – coming next update.</p>');
                break;
            default:
                openModal(game.toUpperCase(), '<p style="text-align:center">🚀 This game is under construction. Stay tuned!</p>');
        }
    });
});


// ========== INVITE FRIEND ==========
document.getElementById('inviteBtn').addEventListener('click', () => {
    const botUsername = "Next_Ludo_Games_bot";  // CHANGE to your bot's username
    const inviteLink = `https://t.me/share/url?url=https://t.me/${botUsername}?start=ref_${user?.id || ''}&text=Join Ludex Games and get 10% cashback!`;
    tg.openTelegramLink(inviteLink);
});

// ========== BOTTOM NAVIGATION (simple) ==========
document.querySelectorAll('.nav-item').forEach(nav => {
    nav.addEventListener('click', () => {
        const navName = nav.getAttribute('data-nav');
        if (navName === 'profile') {
            openModal('My Profile', `
                <p><strong>👤 Name:</strong> ${user?.first_name || 'Guest'}</p>
                <p><strong>🆔 ID:</strong> ${user?.id || 'Not logged in'}</p>
                <p><strong>💰 Balance:</strong> ${currentBalance} Birr</p>
                <p><strong>🎮 Games played:</strong> 0</p>
                <button class="game-action-btn" onclick="window.location.reload()">Refresh</button>
            `);
        } else if (navName === 'transactions') {
            openModal('Transaction History', '<p>📜 Coming soon. Connect backend for full history.</p>');
        } else if (navName === 'support') {
            openModal('Help & Support', '<p>📧 Contact @support_bot</p><p>⚠️ 10% fee applies on all wins.</p>');
        } else {
            // Home: just close modal
            closeModal();
        }
    });
});

// Initial fetch
fetchBalance();