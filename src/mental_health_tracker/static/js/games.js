// Breathing Exercise Game
document.addEventListener('DOMContentLoaded', function() {
    const breathingExercise = document.getElementById('breathing-exercise');
    const startBreathingBtn = document.getElementById('start-breathing');
    const breathingCircle = document.querySelector('.breathing-circle');
    const breathingInstruction = document.querySelector('.breathing-instruction');
    const breathingTimer = document.querySelector('.breathing-timer');
    const breathingMinutes = document.getElementById('breathing-minutes');
    const breathingSeconds = document.getElementById('breathing-seconds');

    let isBreathing = false;
    let timeLeft = 120; // 2 minutes in seconds
    let breathingInterval;
    let timerInterval;

    function startBreathingExercise() {
        if (isBreathing) return;
        
        isBreathing = true;
        startBreathingBtn.textContent = 'Stop Exercise';
        breathingTimer.classList.remove('d-none');
        
        // Start breathing animation
        breathingInterval = setInterval(() => {
            breathingCircle.classList.toggle('expand');
            breathingInstruction.textContent = breathingCircle.classList.contains('expand') ? 'Breathe in' : 'Breathe out';
        }, 4000);

        // Start timer
        timerInterval = setInterval(() => {
            timeLeft--;
            const minutes = Math.floor(timeLeft / 60);
            const seconds = timeLeft % 60;
            breathingMinutes.textContent = minutes.toString().padStart(2, '0');
            breathingSeconds.textContent = seconds.toString().padStart(2, '0');

            if (timeLeft <= 0) {
                stopBreathingExercise();
            }
        }, 1000);
    }

    function stopBreathingExercise() {
        isBreathing = false;
        startBreathingBtn.textContent = 'Start Exercise';
        breathingTimer.classList.add('d-none');
        breathingCircle.classList.remove('expand');
        breathingInstruction.textContent = 'Breathe in';
        clearInterval(breathingInterval);
        clearInterval(timerInterval);
        timeLeft = 120;
    }

    startBreathingBtn.addEventListener('click', () => {
        if (isBreathing) {
            stopBreathingExercise();
        } else {
            startBreathingExercise();
        }
    });

    // Tic Tac Toe Game
    const ticTacToeStartScreen = document.getElementById('tictactoe-start-screen');
    const startTicTacToeBtn = document.getElementById('start-tictactoe-btn');
    let currentPlayer = 'X';
    let gameBoard = ['', '', '', '', '', '', '', '', ''];
    let gameActive = false;

    function createTicTacToeBoard() {
        const board = document.createElement('div');
        board.className = 'tic-tac-toe-board';
        board.innerHTML = `
            <div class="row">
                <div class="cell" data-index="0"></div>
                <div class="cell" data-index="1"></div>
                <div class="cell" data-index="2"></div>
            </div>
            <div class="row">
                <div class="cell" data-index="3"></div>
                <div class="cell" data-index="4"></div>
                <div class="cell" data-index="5"></div>
            </div>
            <div class="row">
                <div class="cell" data-index="6"></div>
                <div class="cell" data-index="7"></div>
                <div class="cell" data-index="8"></div>
            </div>
        `;

        const gameContainer = document.createElement('div');
        gameContainer.className = 'game-container';
        gameContainer.appendChild(board);

        const status = document.createElement('div');
        status.className = 'game-status';
        status.textContent = `Player ${currentPlayer}'s turn`;

        const resetButton = document.createElement('button');
        resetButton.className = 'btn btn-secondary mt-3';
        resetButton.textContent = 'Reset Game';
        resetButton.onclick = resetTicTacToe;

        ticTacToeStartScreen.innerHTML = '';
        ticTacToeStartScreen.appendChild(gameContainer);
        ticTacToeStartScreen.appendChild(status);
        ticTacToeStartScreen.appendChild(resetButton);

        const cells = document.querySelectorAll('.cell');
        cells.forEach(cell => {
            cell.addEventListener('click', handleCellClick);
        });

        gameActive = true;
    }

    function handleCellClick(e) {
        const cell = e.target;
        const index = parseInt(cell.getAttribute('data-index'));

        if (gameBoard[index] !== '' || !gameActive) return;

        gameBoard[index] = currentPlayer;
        cell.textContent = currentPlayer;
        cell.classList.add(currentPlayer.toLowerCase());

        if (checkWin()) {
            document.querySelector('.game-status').textContent = `Player ${currentPlayer} wins!`;
            gameActive = false;
            return;
        }

        if (checkDraw()) {
            document.querySelector('.game-status').textContent = 'Game ended in a draw!';
            gameActive = false;
            return;
        }

        currentPlayer = currentPlayer === 'X' ? 'O' : 'X';
        document.querySelector('.game-status').textContent = `Player ${currentPlayer}'s turn`;
    }

    function checkWin() {
        const winPatterns = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8], // Rows
            [0, 3, 6], [1, 4, 7], [2, 5, 8], // Columns
            [0, 4, 8], [2, 4, 6] // Diagonals
        ];

        return winPatterns.some(pattern => {
            const [a, b, c] = pattern;
            return gameBoard[a] && gameBoard[a] === gameBoard[b] && gameBoard[a] === gameBoard[c];
        });
    }

    function checkDraw() {
        return gameBoard.every(cell => cell !== '');
    }

    function resetTicTacToe() {
        gameBoard = ['', '', '', '', '', '', '', '', ''];
        currentPlayer = 'X';
        gameActive = true;
        document.querySelector('.game-status').textContent = `Player ${currentPlayer}'s turn`;
        document.querySelectorAll('.cell').forEach(cell => {
            cell.textContent = '';
            cell.classList.remove('x', 'o');
        });
    }

    startTicTacToeBtn.addEventListener('click', createTicTacToeBoard);
}); 