# ⚽ PariuBot - Smart Football Betting Analyzer & Tracker

PariuBot is a hybrid (Web/CLI) application designed to eliminate guesswork in sports betting by using the Poisson statistical model for accurate probability calculations, backtracking algorithms for optimized ticket generation, and a Streamlit interface for live result monitoring.

---

## ⚙️ What Does It Do?

1. **Mathematical Engine (Poisson Distribution):** 
   - Analyzes historical home/away statistics (goals scored/conceded, league averages from `statistici_salvate.json`).
   - Computes expected goals ($xG$) for each team and generates exact mathematical probabilities for standard 1X2 and double chance markets ($1, X, 2, 1X, X2$).

2. **Value Bet Detection:**
   - Connects live to **The Odds-API** to fetch real-time bookmaker decimal odds.
   - Compares bookmaker odds with calculated mathematical probabilities ($Odds \times Prob > 0.95$) to identify selections that offer long-term value.

3. **Ticket Generator (Backtracking):**
   - Combines selected matches into accumulator tickets targeting a specific odds profile defined by the user (*SAFE* ~2.0, *MEDIUM* ~5.0, *RISKY* ~15.0, or *Custom*).
   - Enforces strict constraints on match overlap between tickets and minimum event counts per style (*Short* vs. *Long*).

4. **Live Tracking & History:**
   - Saves generated tickets locally into `bilete_salvate.json`.
   - Queries final match results from the API (`FT - Full Time`) to automatically update each ticket's status to: `✅ Won`, `❌ Lost`, or `🟡 Pending`.
   - Allows instant dispatch of generated tickets directly to a private Telegram chat or channel.

---
🌐 **Live Demo:** [Access the live application](https://valuepulse-83vtddvnvd7jgrtbmyq2kt.streamlit.app/)
