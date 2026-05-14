const tg = window.Telegram.WebApp;

tg.expand();

const user = tg.initDataUnsafe.user;

document.getElementById("profile").innerHTML = `
    👤 ${user.first_name}
`;

let balance = 100;

function flipCard(card) {

    const result = document.getElementById("result");

    const random = Math.floor(Math.random() * 3);

    const cards = document.querySelectorAll(".card");

    cards.forEach(c => {

        c.innerHTML = "❌";
    });

    cards[random].innerHTML = "💎";

    if (card === cards[random]) {

        result.innerHTML = "✅ You Won 20 Birr";

        balance += 20;

    } else {

        result.innerHTML = "❌ You Lost 10 Birr";

        balance -= 10;
    }

    document.getElementById("balance").innerText = balance;
}