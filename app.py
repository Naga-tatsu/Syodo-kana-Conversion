import MeCab
import gradio as gr
import random
import ipadic 
import csv # csvをインポート
import os # ファイルパス操作のためにosをインポート

# ipadicの辞書ディレクトリパスを取得
dic_path = ipadic.DICDIR 
TAGGER = None

# ==========================
# 1. kogo-words.csv の読み込み
# ==========================
KOGO_YOMI_MAP = {}
# app.pyと同じ階層にあると仮定
CSV_FILE_PATH = "kogo-words.csv"

try:
    # ファイルの存在を確認
    if not os.path.exists(CSV_FILE_PATH):
        # ファイルがない場合は警告を出して処理を継続（辞書は空のまま）
        print(f"警告: 辞書ファイル '{CSV_FILE_PATH}' が見つかりませんでした。CSV参照はスキップされます。")
    else:
        # 'utf-8' エンコーディングで読み込み
        with open(CSV_FILE_PATH, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            # ヘッダー行をスキップ (もしあれば)
            header = next(reader, None) 
            
            # データ行を読み込み、辞書を作成
            for row in reader:
                # サンプルから、1列目が漢字、2列目が読みと仮定
                if len(row) >= 2 and row[0].strip() and row[1].strip():
                    # 最も長い語句からマッチさせるために、key-valueをそのまま登録
                    # key: 漢字 (例: '山川')
                    # value: 読み (例: 'やまかわ')
                    KOGO_YOMI_MAP[row[0].strip()] = row[1].strip()

    # KOGO_YOMI_MAPを単語の長さ（降順）でソートし、置換時に長い語句からマッチするようにする
    # これは後の置換処理で使用
    SORTED_KOGO_WORDS = sorted(KOGO_YOMI_MAP.keys(), key=len, reverse=True)
    
except Exception as e:
    print(f"CSVファイルの読み込み中にエラーが発生しました: {e}")
    # 辞書参照なしで続行

# ==========================
# 変体仮名 dict（ユーザー定義）
# (中略 - 変更なし)
# ==========================
hentaigana_dict = {
    "あ":["阿"],"う":["有"],"お":["於"],"か":["可"],"き":["幾","支"],"く":["具"],"け":["介"],"こ":["古"],
    "さ":["佐"],"す":["春","寿"],"せ":["勢"],"そ":["所","楚"],"た":["多","堂"],"ち":["遅"],"つ":["徒"],"と":["登"],
    "な":["那"],"に":["尓","耳"],"ね":["年"],"ね":["年"],"の":["能"],"は":["者","盤"],"ひ":["非","悲"],"ふ":["婦","布"],"ほ":["本"],
    "ま":["万","満"],"み":["見","身"],"む":["無"],"め":["免"],"も":["裳"],"や":["夜"],"ゆ":["由"],"よ":["世"],
    "ら":["羅"],"り":["里","累"],"る":["流"],"れ":["連"],"わ":["王"]
}

# MeCab Taggerをグローバルで一度だけ初期化（ipadicの辞書パスと設定ファイルを指定）
try:
    # ipadicの辞書パスを -d (辞書ディレクトリ) と --rcfile (設定ファイル) の両方に指定することで、
    # mecabrc が存在しないエラーを回避し、ipadicの辞書で強制的に初期化を試みる
    TAGGER = MeCab.Tagger(f"-Ochasen -d {dic_path} --rcfile={dic_path}") # ✨ ここを修正
    
except Exception as e:
    # 失敗した場合は、エラーをログに出力して終了
    print("MeCab Tagger の初期化に致命的なエラーが発生しました。")
    print(f"エラー内容: {e}")
    # MeCab本体（libmecab-devなど）がシステムにインストールされているか確認してください。
    raise # プログラムを終了させる

# TAGGERの初期化が成功したかを確認
if TAGGER is None:
    raise RuntimeError("MeCab Taggerの初期化に失敗しました。システム環境を確認してください。")


# ==========================
# 和歌 → ひらがな変換
# ==========================
def waka_to_hiragana(waka: str) -> str:
    # 2. CSV一覧から単語の読みを判断し、入力文字列を置換
    processed_waka = waka
    
    # 長い語句から順に置換することで、「天の原」→「あまのはら」、「天」→「あま」のような誤爆を防ぐ
    for kanji_word in SORTED_KOGO_WORDS:
        yomi = KOGO_YOMI_MAP[kanji_word]
        # 置換後の読みはカタカナ（MeCabのデフォルトの読みフォーマット）にしておく
        # CSVの読みがひらがなの場合: 'やまかわ' -> 'ヤマカワ'
        # CSVの読みがカタカナの場合: 'ヤマカワ' -> 'ヤマカワ' (変換なし)
        katakana_yomi = "".join([
            chr(ord(ch) + 0x60) if "ぁ" <= ch <= "ん" else ch
            for ch in yomi
        ])
        
        # 入力文字列中の漢字を、CSVに定義された読み（カタカナ）に置き換え
        # 置換後の文字列は、MeCabの解析ノードの「読み」として扱われるようにする
        processed_waka = processed_waka.replace(kanji_word, katakana_yomi)

    # 置換後の文字列をMeCabで解析
    # CSVで置換された部分は「読み」が既に確定しているため、MeCabはその「読み」をそのまま採用しやすくなる
    node = TAGGER.parseToNode(processed_waka)

    result = []
    while node:
        if node.surface and node.feature != 'BOS/EOS':
            features = node.feature.split(",")

            # MeCabの解析結果から読みを取得（CSV置換部分はカタカナのまま読みとして取得される）
            if len(features) >= 8 and features[7] != "*":
                yomi = features[7]
            else:
                yomi = node.surface # 読みがない場合は表層形を使用

            # カタカナ → ひらがな変換 (CSVからの読みも含めて全てここで変換)
            hira = "".join([
                chr(ord(ch) - 0x60) if "ァ" <= ch <= "ン" else ch
                for ch in yomi
            ])
            result.append(hira)

        node = node.next
        
    return "".join(result)

# ==========================
# 変体仮名変換（確率調整）
# (変更なし)
# ==========================
def to_hentaigana(hira: str, ratio: float) -> str:
    result = []
    for ch in hira:
        if ch in hentaigana_dict and random.random() < ratio:
            result.append(random.choice(hentaigana_dict[ch]))
        else:
            result.append(ch)
    return "".join(result)

# ==========================
# gradio用関数
# (変更なし)
# ==========================
def process_waka(waka, ratio):
    hira = waka_to_hiragana(waka)
    hentaigana_text = to_hentaigana(hira, ratio)
    output = f"【漢字かな混じり】\n{waka}\n\n"
    output += f"【ひらがな】\n{hira}\n\n"
    output += f"【変体仮名（混ざり度 {ratio:.1f}）】\n{hentaigana_text}"
    return output

# ==========================
# Gradio UI
# (変更なし)
# ==========================

with gr.Blocks() as demo:
    gr.Markdown(
        """
        ## 古筆 → ひらがな & 変体仮名変換
        - 漢字混じりの文をひらがなと変体仮名に変換します
        - 変換度合いはスライドバーで調整できます
        - ひらがな変換は自動のため、誤りがある可能性があります
        """
    )
    
    inp = gr.Textbox(label="和歌を入力", placeholder="例：この道や行く人なしに秋の暮")
    slider = gr.Slider(0.2, 0.8, value=0.5, step=0.1, label="変体仮名の混ざり度合い")
        
    btn = gr.Button("変換する")
    
    out = gr.Textbox(
        label="出力結果",
        lines=8,
        show_copy_button=True,
        interactive=False
    )
    
    btn.click(fn=process_waka, inputs=[inp, slider], outputs=out)

demo.launch()