import shutil
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask import render_template, request, redirect, url_for, send_file
from datetime import datetime, timedelta, timezone
JST = timezone(timedelta(hours=+9), 'JST')

app = Flask(__name__)
app.config.from_object('config')

db = SQLAlchemy(app)

class Player(db.Model):
    __tablename__ = 'players'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)

class Tournament(db.Model):
    __tablename__ = 'tournaments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)

class Result(db.Model):
    __tablename__ = 'results'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    house = db.Column(db.String, nullable=False) # 東家など
    rank = db.Column(db.Integer, nullable=False) # 順位
    score = db.Column(db.Integer, nullable=False) # 持ち点
    total_points = db.Column(db.Integer, nullable=False) 
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'))
    # ゲームとのリレーションシップ
    game = db.relationship("Game", back_populates="result")

class Game(db.Model):
    __tablename__ = 'games'
    id = db.Column(db.Integer, primary_key=True)
    time = db.Column(db.DateTime, nullable=False, default=datetime.now(JST))
    tournament = db.Column(db.String, nullable=True)
    # リザルトとのリレーションシップ
    result = db.relationship("Result", back_populates="game", cascade="all, delete-orphan")

def RD(value):
    return round(value, 1)

@app.route('/', methods=['GET', 'POST'])
def flask_app():
    players = Player.query.all()
    player_names = [player.name for player in players]
    tournaments = Tournament.query.all()
    tournament_names = [tournament.name for tournament in tournaments]
    tournament_names.insert(0, "全て")
    DATA = []
    if request.method == 'GET':
        for i in player_names:
            results = Result.query.filter_by(name=i).all()
            match_count = len(results)
            if match_count == 0:
                continue
            rank_count = [0, 0, 0, 0]
            point_sum = 0
            score_max = 0
            for j in results:
                rank_count[j.rank-1] += 1
                point_sum += j.total_points
                if score_max < j.score:
                    score_max = j.score
            ave_rank = (rank_count[0] + rank_count[1]*2 + rank_count[2]*3 + rank_count[3]*4)/match_count #平着
            top = rank_count[0]/match_count # トップ率
            last_esc = (match_count - rank_count[3])/match_count # ラス回避率
            DATA.append([i, match_count, RD(point_sum), RD(ave_rank), rank_count[0], rank_count[1], rank_count[2], rank_count[3], RD(top), RD(last_esc), score_max, RD(point_sum/match_count)])
        DATA.sort(key=lambda x: x[2], reverse=True) # 合計ポイントで降順にソート
        DATA2 = DATA.copy()
        DATA2.sort(key=lambda x: x[11], reverse=True) # 平均ポイントで降順にソート
        return render_template('main/index.html', results=DATA, results2=DATA2, tournament_names=tournament_names, default_name="全て")
    if request.method == 'POST':
        form_T = request.form.get('T')
        if form_T == "全て":
            return redirect(url_for('flask_app'))
        for i in player_names:
            results = (
                Result.query
                .join(Game)  # `Result` テーブルと `Game` テーブルを結合
                .filter(Game.tournament == form_T, Result.name == i)
                .all()
            )
            match_count = len(results)
            if match_count == 0:
                continue
            rank_count = [0, 0, 0, 0]
            point_sum = 0
            score_max = 0
            for j in results:
                rank_count[j.rank-1] += 1
                point_sum += j.total_points
                if score_max < j.score:
                    score_max = j.score
            ave_rank = (rank_count[0] + rank_count[1]*2 + rank_count[2]*3 + rank_count[3]*4)/match_count #平着
            top = rank_count[0]/match_count # トップ率
            last_esc = (match_count - rank_count[3])/match_count # ラス回避率
            DATA.append([i, match_count, RD(point_sum), RD(ave_rank), rank_count[0], rank_count[1], rank_count[2], rank_count[3], RD(top), RD(last_esc), score_max, RD(point_sum/match_count)])
        DATA.sort(key=lambda x: x[2], reverse=True) # 合計ポイントで降順にソート
        DATA2 = DATA.copy()
        DATA2.sort(key=lambda x: x[11], reverse=True) # 平均ポイントで降順にソート
        return render_template('main/index.html', results=DATA, results2=DATA2, tournament_names=tournament_names, default_name=form_T)

@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'GET':
        players = Player.query.all()
        player_names = [player.name for player in players]
        tournaments = Tournament.query.all()
        tournament_names = [tournament.name for tournament in tournaments]
        return render_template('add/index.html', player_names=player_names, tournament_names=tournament_names)
    if request.method == 'POST':
        if 'submit_button1' in request.form:
            form_Tname = request.form.get('Tname')  # str
            form_Nname = request.form.get('Nname')  # str
            form_Sname = request.form.get('Sname')  # str
            form_Pname = request.form.get('Pname')  # str
            form_Tscore = request.form.get('Tscore', type=int)
            form_Nscore = request.form.get('Nscore', type=int)
            form_Sscore = request.form.get('Sscore', type=int)
            form_Pscore = request.form.get('Pscore', type=int)

            form_name = [form_Tname, form_Nname, form_Sname, form_Pname]
            form_score = [form_Tscore, form_Nscore, form_Sscore, form_Pscore]
            form_point = [round((i-30000)/1000, 1) for i in form_score]
            oka = [20, 0, 0, 0]
            uma = [30, 10, -10, -30]
            house = ["東家", "南家", "西家", "北家"]
            rank = [0, 0, 0, 0]

            # 順位順に並び替える
            indexed_list = list(enumerate(form_point)) # 元のリストとインデックスのタプルのリストを作成
            sorted_indexed_list = sorted(indexed_list, key=lambda x: x[1], reverse=True) # 降順でソート
            sorted_indices = [item[0] for item in sorted_indexed_list] # ソート後の元のインデックス
            rank[sorted_indices[0]], rank[sorted_indices[1]], rank[sorted_indices[2]], rank[sorted_indices[3]] = 1, 2, 3, 4
            if form_point[sorted_indices[0]] == form_point[sorted_indices[1]]:
                rank[sorted_indices[0]], rank[sorted_indices[1]], rank[sorted_indices[2]], rank[sorted_indices[3]] = 1, 1, 3, 4
                oka = [10, 10, 0, 0]
                uma = [20, 20, -10, -30]
            if form_point[sorted_indices[1]] == form_point[sorted_indices[2]]:
                rank[sorted_indices[0]], rank[sorted_indices[1]], rank[sorted_indices[2]], rank[sorted_indices[3]] = 1, 2, 2, 4
                uma = [30, 0, 0, -30]
            if form_point[sorted_indices[2]] == form_point[sorted_indices[3]]:
                rank[sorted_indices[0]], rank[sorted_indices[1]], rank[sorted_indices[2]], rank[sorted_indices[3]] = 1, 2, 3, 3
                uma = [30, 10, -20, -20]

            form_T = request.form.get('T')
            game = Game(tournament=form_T)
            db.session.add(game)
            db.session.commit()
            game_id = game.id # 追加したレコードのID取得

            for i in sorted_indices:
                message = Result(
                    name=form_name[i],
                    house=house[i],
                    rank=rank[i],
                    score=form_score[i],
                    total_points=form_point[i]+oka[rank[i]-1]+uma[rank[i]-1],
                    game_id=game_id
                )
                db.session.add(message)
                db.session.commit()
            
            timestamp = datetime.now(JST).strftime('%Y%m%d_%H%M%S') # 履歴を保存しておく．
            destination_file = f'log/game_scores_{timestamp}.db' # 環境によってパスが変わる場合あり．
            shutil.copy('instance/game_scores.db', destination_file) # ファイルをコピーして新しい名前を付ける

        elif 'submit_button2' in request.form:
            form_name = request.form.get('name')  # str
            message = Player(name=form_name)
            db.session.add(message)
            db.session.commit()
            return redirect(url_for('add'))

        elif 'submit_button3' in request.form:
            form_name = request.form.get('name')  # str
            message = Tournament(name=form_name)
            db.session.add(message)
            db.session.commit()
            return redirect(url_for('add'))

        return redirect(url_for('flask_app'))

@app.route('/data')
def data_list():
    results = Result.query.all()
    return render_template('data/index.html', results=results)

@app.route('/data/game')
def game_list():
    games = Game.query.all()
    results_ = Result.query.all()
    results = [results_[i:i + 4] for i in range(0, len(results_), 4)]
    rank_name = []
    for i in results:
        temp = [" ", " ", " ", " "]
        for j in i:
            temp[j.rank-1] += j.name + " "
        rank_name.append(temp)

    combined_list = list(zip(games, rank_name))
    return render_template('data/game.html', games=combined_list)

@app.route('/data/game/<int:id>')
def game_result(id):
    results = Result.query.filter_by(game_id=id).order_by(Result.score.desc()).all()
    return render_template('data/game_result.html', results=results)

@app.route('/data/game/<int:id>/edit', methods=['GET'])
def game_edit(id):
    results = Result.query.filter_by(game_id=id).all()
    tournaments = Tournament.query.all()
    tournament_names = [tournament.name for tournament in tournaments]
    now_tournament_name = Game.query.get(id)
    return render_template('data/game_edit.html', results=results, tournament_names=tournament_names, now_tournament_name=now_tournament_name.tournament)

@app.route('/data/game/<int:id>/update', methods=['POST'])
def game_update(id):
    if 'submit_button1' in request.form:
        form_Tscore = request.form.get('Tscore', type=int)
        form_Nscore = request.form.get('Nscore', type=int)
        form_Sscore = request.form.get('Sscore', type=int)
        form_Pscore = request.form.get('Pscore', type=int)

        form_score = [form_Tscore, form_Nscore, form_Sscore, form_Pscore]
        form_point = [round((i-30000)/1000, 1) for i in form_score]
        oka = [20, 0, 0, 0]
        uma = [30, 10, -10, -30]
        rank = [0, 0, 0, 0]

        # 順位順に並び替える
        indexed_list = list(enumerate(form_point)) # 元のリストとインデックスのタプルのリストを作成
        sorted_indexed_list = sorted(indexed_list, key=lambda x: x[1], reverse=True) # 降順でソート
        sorted_indices = [item[0] for item in sorted_indexed_list] # ソート後の元のインデックス
        rank[sorted_indices[0]], rank[sorted_indices[1]], rank[sorted_indices[2]], rank[sorted_indices[3]] = 1, 2, 3, 4
        if form_point[sorted_indices[0]] == form_point[sorted_indices[1]]:
            rank[sorted_indices[0]], rank[sorted_indices[1]], rank[sorted_indices[2]], rank[sorted_indices[3]] = 1, 1, 3, 4
            oka = [10, 10, 0, 0]
            uma = [20, 20, -10, -30]
        if form_point[sorted_indices[1]] == form_point[sorted_indices[2]]:
            rank[sorted_indices[0]], rank[sorted_indices[1]], rank[sorted_indices[2]], rank[sorted_indices[3]] = 1, 2, 2, 4
            uma = [30, 0, 0, -30]
        if form_point[sorted_indices[2]] == form_point[sorted_indices[3]]:
            rank[sorted_indices[0]], rank[sorted_indices[1]], rank[sorted_indices[2]], rank[sorted_indices[3]] = 1, 2, 3, 3
            uma = [30, 10, -20, -20]

        results = Result.query.filter_by(game_id=id).all()
        results = [results[i] for i in sorted_indices]
        for i, result in zip(sorted_indices, results):
            result.rank=rank[i]
            result.score=form_score[i]
            result.total_points=form_point[i]+oka[rank[i]-1]+uma[rank[i]-1]
        
        game = Game.query.get(id)
        new_name = request.form.get('T') # 変更後の名前
        game.tournament = new_name
        db.session.commit()
    elif 'submit_button2' in request.form:
        game = Game.query.get(id)
        db.session.delete(game) 
        results = Result.query.filter_by(game_id=id).all()
        for result in results:
            db.session.delete(result) 
        db.session.commit()
    return redirect(url_for('game_list'))

@app.route('/data/player')
def player_list():
    players = Player.query.all()
    return render_template('data/player.html', players=players)

@app.route('/data/player/<int:id>/edit', methods=['GET'])
def player_edit(id):
    player = Player.query.get(id)
    return render_template('data/player_edit.html', player=player)

@app.route('/data/player/<int:id>/update', methods=['POST'])
def player_update(id):
    player = Player.query.get(id)
    pre_name = player.name # 変更前の名前
    new_name = request.form.get('name') # 変更後の名前
    player.name = new_name 
    db.session.merge(player)
    db.session.commit()

    # Resultテーブル内の名前も変更
    results = Result.query.filter_by(name=pre_name).all()
    for result in results:
        result.name = new_name
    db.session.commit()
    return redirect(url_for('player_list'))

@app.route('/data/tournament')
def tournament_list():
    tournaments = Tournament.query.all()
    return render_template('data/tournament.html', tournaments=tournaments)

@app.route('/data/tournament/<int:id>/edit', methods=['GET'])
def tournament_edit(id):
    tournament = Tournament.query.get(id)
    return render_template('data/tournament_edit.html', tournament=tournament)

@app.route('/data/tournament/<int:id>/update', methods=['POST'])
def tournament_update(id):
    tournament = Tournament.query.get(id)
    pre_name = tournament.name # 変更前の大会名
    new_name = request.form.get('name') # 変更後の大会名
    tournament.name = new_name 
    db.session.merge(tournament)
    db.session.commit()

    # Gameテーブル内の大会名も変更
    games = Game.query.filter_by(tournament=pre_name).all()
    for game in games:
        game.tournament = new_name
    db.session.commit()
    return redirect(url_for('tournament_list'))

@app.route('/setting', methods=['GET', 'POST'])
def setting():
    if request.method == 'GET':
        return render_template('setting/index.html')
    if request.method == 'POST':
        if 'submit_button1' in request.form:
            with app.app_context():
                db.drop_all()
                db.create_all()
        if 'submit_button2' in request.form:
            try:
                return send_file('game_scores.db', as_attachment=True)
            except FileNotFoundError:
                return "File not found.", 404
    return redirect(url_for('flask_app'))

if __name__ == '__main__':
    #with app.app_context():
    #    db.create_all()  # これでテーブルが作成されます
    app.run(debug=True, host='0.0.0.0', port=5000)
    #app.run(debug=False, host='0.0.0.0', port=5000)