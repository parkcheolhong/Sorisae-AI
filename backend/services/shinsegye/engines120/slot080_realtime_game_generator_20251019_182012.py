"""
🎮 AI 기반 실시간 게임 생성기
사용자 음성 명령으로 즉석에서 미니게임을 생성하고 실행
"""

import random
import json
import os
from datetime import datetime
from typing import Dict, List, Any
import time

class RealTimeGameGenerator:
    def __init__(self):
        self.game_templates = {
            "퍼즐": {
                "types": ["숫자퍼즐", "단어퍼즐", "논리퍼즐", "수학퍼즐"],
                "difficulty": ["쉬움", "보통", "어려움"],
                "mechanics": ["매칭", "순서맞추기", "패턴찾기", "계산"]
            },
            "액션": {
                "types": ["타이핑게임", "반응속도", "기억력게임", "순발력게임"],
                "difficulty": ["쉬움", "보통", "어려움"],
                "mechanics": ["빠른입력", "정확성", "기억", "반사신경"]
            },
            "전략": {
                "types": ["가위바위보+", "숫자전략", "단어전략", "코드전략"],
                "difficulty": ["쉬움", "보통", "어려움"],
                "mechanics": ["예측", "계획", "적응", "최적화"]
            },
            "학습": {
                "types": ["코딩퀴즈", "개념학습", "실습게임", "문제해결"],
                "difficulty": ["초급", "중급", "고급"],
                "mechanics": ["문제풀이", "개념이해", "코드작성", "디버깅"]
            }
        }
        
        self.generated_games = []
        self.game_stats = {}
    
    def parse_game_request(self, command: str) -> Dict:
        """음성 명령에서 게임 요구사항 추출"""
        request = {
            "type": "퍼즐",  # 기본값
            "difficulty": "보통",
            "theme": "일반",
            "duration": "짧음",
            "players": 1
        }
        
        # 게임 타입 감지
        if any(word in command for word in ["퍼즐", "puzzle", "수수께끼"]):
            request["type"] = "퍼즐"
        elif any(word in command for word in ["액션", "빠른", "반응", "타이핑"]):
            request["type"] = "액션"
        elif any(word in command for word in ["전략", "계획", "생각"]):
            request["type"] = "전략"
        elif any(word in command for word in ["학습", "공부", "코딩", "프로그래밍"]):
            request["type"] = "학습"
        
        # 난이도 감지
        if any(word in command for word in ["쉬운", "간단한", "초급"]):
            request["difficulty"] = "쉬움"
        elif any(word in command for word in ["어려운", "복잡한", "고급"]):
            request["difficulty"] = "어려움"
        
        # 테마 감지
        if any(word in command for word in ["숫자", "수학", "계산"]):
            request["theme"] = "수학"
        elif any(word in command for word in ["단어", "글자", "언어"]):
            request["theme"] = "언어"
        elif any(word in command for word in ["코드", "프로그래밍", "개발"]):
            request["theme"] = "코딩"
        
        return request
    
    def generate_puzzle_game(self, difficulty: str, theme: str) -> Dict:
        """퍼즐 게임 생성"""
        if theme == "수학":
            if difficulty == "쉬움":
                num1, num2 = random.randint(1, 10), random.randint(1, 10)
                operation = random.choice(["+", "-", "*"])
                if operation == "+":
                    answer = num1 + num2
                elif operation == "-":
                    answer = max(num1, num2) - min(num1, num2)
                    num1, num2 = max(num1, num2), min(num1, num2)
                else:
                    answer = num1 * num2
                
                return {
                    "name": "간단한 수학 퍼즐",
                    "question": f"{num1} {operation} {num2} = ?",
                    "answer": str(answer),
                    "type": "input",
                    "hints": [f"답은 한 자리 또는 두 자리 수입니다", f"계산을 차근차근 해보세요"]
                }
            
            elif difficulty == "어려움":
                # 연속 계산 문제
                nums = [random.randint(1, 20) for _ in range(3)]
                ops = [random.choice(["+", "-", "*"]) for _ in range(2)]
                
                question = f"{nums[0]} {ops[0]} {nums[1]} {ops[1]} {nums[2]} = ?"
                # 왼쪽부터 계산
                result = nums[0]
                if ops[0] == "+":
                    result += nums[1]
                elif ops[0] == "-":
                    result -= nums[1]
                else:
                    result *= nums[1]
                
                if ops[1] == "+":
                    result += nums[2]
                elif ops[1] == "-":
                    result -= nums[2]
                else:
                    result *= nums[2]
                
                return {
                    "name": "연속 계산 퍼즐",
                    "question": question,
                    "answer": str(result),
                    "type": "input",
                    "hints": ["왼쪽부터 순서대로 계산하세요", "계산기 없이 도전해보세요!"]
                }
        
        elif theme == "언어":
            words = ["프로그래밍", "개발자", "알고리즘", "데이터베이스", "인공지능"]
            word = random.choice(words)
            scrambled = list(word)
            random.shuffle(scrambled)
            
            return {
                "name": "단어 맞추기 퍼즐",
                "question": f"다음 글자를 정렬하여 단어를 만드세요: {''.join(scrambled)}",
                "answer": word,
                "type": "input",
                "hints": [f"IT 관련 용어입니다", f"글자 수: {len(word)}자"]
            }
        
        # 기본 숫자 퍼즐
        target = random.randint(1, 100)
        return {
            "name": "숫자 맞추기 게임",
            "question": f"1부터 100 사이의 숫자를 맞춰보세요! (목표: {target})",
            "answer": str(target),
            "type": "guess",
            "hints": ["너무 높거나 낮으면 힌트를 드릴게요", "10번 안에 맞춰보세요!"],
            "max_attempts": 10
        }
    
    def generate_action_game(self, difficulty: str) -> Dict:
        """액션 게임 생성"""
        if difficulty == "쉬움":
            words = ["hello", "world", "code", "game", "fun"]
        elif difficulty == "어려움":
            words = ["programming", "algorithm", "development", "artificial", "intelligence"]
        else:
            words = ["python", "javascript", "function", "variable", "loop"]
        
        target_word = random.choice(words)
        
        return {
            "name": "타이핑 스피드 게임",
            "question": f"다음 단어를 빠르게 타이핑하세요: {target_word}",
            "answer": target_word,
            "type": "speed",
            "time_limit": max(len(target_word), 5),
            "hints": ["정확성과 속도 모두 중요해요!", "오타 없이 도전해보세요!"]
        }
    
    def generate_coding_game(self, difficulty: str) -> Dict:
        """코딩 학습 게임 생성"""
        if difficulty == "쉬움":
            questions = [
                {
                    "question": "변수 x에 10을 저장하는 Python 코드는?",
                    "answer": "x = 10",
                    "options": ["x = 10", "x == 10", "x := 10", "var x = 10"]
                },
                {
                    "question": "리스트 [1, 2, 3]에서 첫 번째 요소는?",
                    "answer": "1",
                    "options": ["0", "1", "2", "3"]
                }
            ]
        else:
            questions = [
                {
                    "question": "Python에서 딕셔너리의 값을 안전하게 가져오는 메서드는?",
                    "answer": "get()",
                    "options": ["get()", "fetch()", "retrieve()", "obtain()"]
                },
                {
                    "question": "리스트 컴프리헨션으로 1~10의 제곱을 만들면?",
                    "answer": "[x**2 for x in range(1,11)]",
                    "options": ["[x**2 for x in range(1,11)]", "[x^2 for x in 1:10]", "[x*x in range(10)]", "square(1,10)"]
                }
            ]
        
        question_data = random.choice(questions)
        return {
            "name": "코딩 퀴즈",
            "question": question_data["question"],
            "answer": question_data["answer"],
            "options": question_data["options"],
            "type": "multiple_choice",
            "hints": ["차근차근 생각해보세요", "정확한 문법이 중요해요!"]
        }
    
    def create_game(self, command: str) -> Dict:
        """명령어 기반 게임 생성"""
        request = self.parse_game_request(command)
        
        game_id = f"game_{len(self.generated_games) + 1}_{datetime.now().strftime('%H%M%S')}"
        
        if request["type"] == "퍼즐":
            game_data = self.generate_puzzle_game(request["difficulty"], request["theme"])
        elif request["type"] == "액션":
            game_data = self.generate_action_game(request["difficulty"])
        elif request["type"] == "학습":
            game_data = self.generate_coding_game(request["difficulty"])
        else:
            # 기본 퍼즐 게임
            game_data = self.generate_puzzle_game("보통", "일반")
        
        game = {
            "id": game_id,
            "created": datetime.now().isoformat(),
            "request": request,
            "data": game_data,
            "status": "ready",
            "score": 0,
            "attempts": 0
        }
        
        self.generated_games.append(game)
        return game
    
    def play_game(self, game: Dict, user_input: str) -> Dict:
        """게임 플레이 로직"""
        result = {
            "success": False,
            "message": "",
            "hint": "",
            "game_over": False
        }
        
        game_data = game["data"]
        game["attempts"] += 1
        
        if game_data["type"] == "input":
            if user_input.strip().lower() == game_data["answer"].lower():
                result["success"] = True
                result["message"] = f"🎉 정답입니다! '{game_data['answer']}'"
                game["score"] = 100 - (game["attempts"] - 1) * 10
                result["game_over"] = True
            else:
                result["message"] = f"❌ 틀렸습니다. 다시 시도해보세요!"
                if game["attempts"] < len(game_data.get("hints", [])):
                    result["hint"] = game_data["hints"][game["attempts"] - 1]
                
                if game["attempts"] >= game_data.get("max_attempts", 5):
                    result["message"] += f" 정답은 '{game_data['answer']}'였습니다."
                    result["game_over"] = True
        
        elif game_data["type"] == "multiple_choice":
            if user_input.strip() == game_data["answer"]:
                result["success"] = True
                result["message"] = "🎉 정답입니다!"
                game["score"] = 100
                result["game_over"] = True
            else:
                result["message"] = f"❌ 틀렸습니다. 정답은 '{game_data['answer']}'입니다."
                result["game_over"] = True
        
        elif game_data["type"] == "guess":
            try:
                user_num = int(user_input.strip())
                target_num = int(game_data["answer"])
                
                if user_num == target_num:
                    result["success"] = True
                    result["message"] = f"🎉 정답입니다! {target_num}"
                    game["score"] = 100 - (game["attempts"] - 1) * 10
                    result["game_over"] = True
                elif user_num < target_num:
                    result["message"] = "📈 더 큰 수입니다!"
                else:
                    result["message"] = "📉 더 작은 수입니다!"
                
                if game["attempts"] >= game_data.get("max_attempts", 10):
                    result["message"] += f" 정답은 {target_num}였습니다."
                    result["game_over"] = True
            except:
                result["message"] = "숫자를 입력해주세요!"
        
        return result

def create_game_response(command: str) -> str:
    """소리새용 게임 생성 응답"""
    generator = RealTimeGameGenerator()
    
    if "게임" in command and ("만들" in command or "생성" in command):
        game = generator.create_game(command)
        return f"""🎮 게임을 생성했습니다!

🏷️ {game['data']['name']}
❓ {game['data']['question']}

게임 ID: {game['id'][-6:]}
답을 말씀해주세요!"""
    
    else:
        return "🎮 게임 생성기가 준비되었습니다! '퍼즐 게임 만들어줘', '코딩 퀴즈 만들어줘' 등을 말씀해보세요."

if __name__ == "__main__":
    # 테스트
    generator = RealTimeGameGenerator()
    
    print("🎮 AI 게임 생성기 테스트")
    print("="*40)
    
    # 다양한 게임 생성 테스트
    commands = [
        "간단한 수학 퍼즐 게임 만들어줘",
        "어려운 코딩 퀴즈 만들어줘",
        "타이핑 게임 만들어줘"
    ]
    
    for cmd in commands:
        print(f"\n명령: {cmd}")
        game = generator.create_game(cmd)
        print(f"게임: {game['data']['name']}")
        print(f"문제: {game['data']['question']}")
        print(f"정답: {game['data']['answer']}")
        print("-" * 30)