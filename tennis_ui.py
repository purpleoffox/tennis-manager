import streamlit as st
import pandas as pd
import random
import json
import os
from typing import List

# ==========================================
# [S] Core Data Structures
# ==========================================

class Player:
    def __init__(self, name: str):
        self.name = name
        self.games_played = 0
        self.stats = {"wins": 0, "losses": 0, "score_diff": 0}
        self.history = {"partner": {}, "opponent": {}}

    def to_dict(self):
        return {
            "name": self.name,
            "games_played": self.games_played,
            "stats": self.stats,
            "history": self.history
        }
    
    @classmethod
    def from_dict(cls, data):
        p = cls(data["name"])
        p.games_played = data["games_played"]
        p.stats = data["stats"]
        p.history = data["history"]
        return p

    def update_stat(self, won: bool, score_diff: int):
        self.games_played += 1
        if won:
            self.stats["wins"] += 1
        else:
            self.stats["losses"] += 1
        self.stats["score_diff"] += score_diff

    def record_match_relations(self, partner, opponent1, opponent2):
        self.history["partner"][partner.name] = self.history["partner"].get(partner.name, 0) + 1
        self.history["opponent"][opponent1.name] = self.history["opponent"].get(opponent1.name, 0) + 1
        self.history["opponent"][opponent2.name] = self.history["opponent"].get(opponent2.name, 0) + 1

class Match:
    def __init__(self, match_id: int, team_a: List[Player], team_b: List[Player]):
        self.id = match_id
        self.team_a = team_a
        self.team_b = team_b
        self.result = (0, 0)
        self.is_finished = False

    def to_dict(self):
        return {
            "id": self.id,
            "team_a_names": [p.name for p in self.team_a],
            "team_b_names": [p.name for p in self.team_b],
            "result": self.result,
            "is_finished": self.is_finished
        }

# ==========================================
# [M] Logic Modules
# ==========================================

class SchedulerEngine:
    def __init__(self, players: List[Player]):
        self.players = players
        self.matches: List[Match] = []

    def calculate_cost(self, p1, p2, p3, p4) -> int:
        cost = 0
        cost += p1.history["partner"].get(p2.name, 0) * 5
        cost += p3.history["partner"].get(p4.name, 0) * 5
        opponents_check = [(p1, p3), (p1, p4), (p2, p3), (p2, p4)]
        for pa, pb in opponents_check:
            cost += pa.history["opponent"].get(pb.name, 0) * 2
        return cost

    def generate_schedule(self, games_per_player: int) -> List[Match]:
        total_matches = (len(self.players) * games_per_player) // 4
        new_matches = []
        
        for p in self.players:
            p.games_played = 0

        for i in range(total_matches):
            candidates = [p for p in self.players if p.games_played < games_per_player]
            random.shuffle(candidates)
            best_match_tuple = None
            min_cost = 999999
            
            attempts = 0
            while attempts < 300:
                attempts += 1
                if len(candidates) < 4: break
                picks = random.sample(candidates, 4)
                p1, p2, p3, p4 = picks[0], picks[1], picks[2], picks[3]
                current_cost = self.calculate_cost(p1, p2, p3, p4)
                if current_cost < min_cost:
                    min_cost = current_cost
                    best_match_tuple = (p1, p2, p3, p4)
                if min_cost == 0: break
            
            if best_match_tuple:
                p1, p2, p3, p4 = best_match_tuple
                for p in [p1, p2, p3, p4]: p.games_played += 1
                p1.record_match_relations(p2, p3, p4)
                p2.record_match_relations(p1, p3, p4)
                p3.record_match_relations(p4, p1, p2)
                p4.record_match_relations(p3, p1, p2)
                new_matches.append(Match(i + 1, [p1, p2], [p3, p4]))
        
        for p in self.players: p.games_played = 0
        return new_matches

def save_data(filename, players, matches, n_games):
    # Streamlit Cloud에서는 파일 저장이 휘발성입니다. 
    # 하지만 세션 유지를 위해 기능은 남겨둡니다.
    pass 

# ==========================================
# [UI] Streamlit Interface
# ==========================================

st.set_page_config(page_title="Tennis Mix Match", page_icon="🎾", layout="wide")

if 'players' not in st.session_state:
    st.session_state.players = []
if 'matches' not in st.session_state:
    st.session_state.matches = []
if 'n_games' not in st.session_state:
    st.session_state.n_games = 0
if 'system_ready' not in st.session_state:
    st.session_state.system_ready = False

with st.sidebar:
    st.header("⚙️ 대회 설정")
    st.subheader("새 대회 시작")
    input_names = st.text_area("참가자 이름 (쉼표로 구분)", "A, B, C, D, E, F, G, H")
    input_n = st.number_input("인당 게임 수", min_value=1, value=4)
    
    if st.button("🚀 대진표 생성"):
        names_list = [n.strip() for n in input_names.split(",") if n.strip()]
        total_slots = len(names_list) * input_n
        
        if total_slots % 4 != 0:
            st.error(f"총 슬롯({total_slots})이 4의 배수가 아닙니다.")
        else:
            players = [Player(name) for name in names_list]
            scheduler = SchedulerEngine(players)
            matches = scheduler.generate_schedule(input_n)
            
            st.session_state.players = players
            st.session_state.matches = matches
            st.session_state.n_games = input_n
            st.session_state.system_ready = True
            st.success("대진표가 생성되었습니다!")
            st.rerun()

st.title("🎾 테니스 복식 대회 매니저")

if not st.session_state.system_ready:
    st.info("👈 왼쪽 사이드바에서 대회를 설정하고 '대진표 생성'을 눌러주세요.")
else:
    tab1, tab2, tab3 = st.tabs(["📝 경기 결과 입력", "📊 실시간 순위", "📅 전체 대진표"])

    with tab1:
        st.subheader("경기 결과 입력")
        pending_matches = [m for m in st.session_state.matches if not m.is_finished]
        
        if not pending_matches:
            st.balloons()
            st.success("모든 경기가 종료되었습니다! 🎉")
        else:
            match_options = {f"Match {m.id}: {m.team_a[0].name}/{m.team_a[1].name} vs {m.team_b[0].name}/{m.team_b[1].name}": m for m in pending_matches}
            selected_option = st.selectbox("진행할 경기를 선택하세요:", list(match_options.keys()))
            
            if selected_option:
                target_match = match_options[selected_option]
                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    sa = st.number_input("Team A 점수", min_value=0, step=1, key="sa")
                with c2:
                    sb = st.number_input("Team B 점수", min_value=0, step=1, key="sb")
                with c3:
                    st.write(" ")
                    st.write(" ")
                    if st.button("입력", type="primary"):
                        target_match.result = (sa, sb)
                        target_match.is_finished = True
                        diff = abs(sa - sb)
                        team_a_won = sa > sb
                        for p in target_match.team_a: p.update_stat(team_a_won, diff if team_a_won else -diff)
                        for p in target_match.team_b: p.update_stat(not team_a_won, diff if not team_a_won else -diff)
                        st.success("저장됨!")
                        st.rerun()

    with tab2:
        rank_data = [{"이름": p.name, "승": p.stats["wins"], "득실": p.stats["score_diff"], "경기": p.games_played} for p in st.session_state.players]
        if rank_data:
            df = pd.DataFrame(rank_data).sort_values(by=["승", "득실"], ascending=[False, False])
            df.index += 1
            st.dataframe(df, use_container_width=True)

    with tab3:
        sch_data = [{"No": m.id, "Team A": f"{m.team_a[0].name},{m.team_a[1].name}", "점수": f"{m.result[0]}:{m.result[1]}" if m.is_finished else "-", "Team B": f"{m.team_b[0].name},{m.team_b[1].name}"} for m in st.session_state.matches]
        if sch_data:
            st.dataframe(pd.DataFrame(sch_data), use_container_width=True)
