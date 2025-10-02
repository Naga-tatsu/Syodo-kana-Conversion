import MeCab
import gradio as gr
import random
import ipadic # ipadicをインポート

# ipadicの辞書ディレクトリパスを取得
dic_path = ipadic.DICDIR 
TAGGER = None

# ==========================
# 変体仮名 dict（ユーザー定義）
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
    # 変更なし
    node = TAGGER.parseToNode(waka)

    result = []
    while node:
        if node.surface and node.feature != 'BOS/EOS':
            features = node.feature.split(",")

            if len(features) >= 8 and features[7] != "*":
                yomi = features[7]
            else:
                yomi = node.surface

            # カタカナ → ひらがな変換
            hira = "".join([
                chr(ord(ch) - 0x60) if "ァ" <= ch <= "ン" else ch
                for ch in yomi
            ])
            result.append(hira)

        node = node.next
    return "".join(result)

# ==========================
# 変体仮名変換（確率調整）
# ==========================
def to_hentaigana(hira: str, ratio: float) -> str:
    # 変更なし
    result = []
    for ch in hira:
        if ch in hentaigana_dict and random.random() < ratio:
            result.append(random.choice(hentaigana_dict[ch]))
        else:
            result.append(ch)
    return "".join(result)

# ==========================
# gradio用関数
# ==========================
def process_waka(waka, ratio):
    # 変更なし
    hira = waka_to_hiragana(waka)
    hentaigana_text = to_hentaigana(hira, ratio)
    output = f"【漢字かな混じり】\n{waka}\n\n"
    output += f"【ひらがな】\n{hira}\n\n"
    output += f"【変体仮名（混ざり度 {ratio:.1f}）】\n{hentaigana_text}"
    return output

# ==========================
# Gradio UI
# ==========================

with gr.Blocks() as demo:
    gr.Markdown("## 和歌 → ひらがな & 変体仮名変換")
    
    # 💡 gr.Row() を削除し、コンポーネントを縦に並べる
    inp = gr.Textbox(label="和歌を入力", placeholder="例：この道や行く人なしに秋の暮")
    slider = gr.Slider(0.2, 0.8, value=0.5, step=0.1, label="変体仮名の混ざり度合い")
        
    btn = gr.Button("変換する")
    
    # 出力結果のTextboxを定義
    out = gr.Textbox(
        label="出力結果",
        lines=8,
        show_copy_button=True,
        interactive=False
    )
    
    # コンポーネントの定義順序がそのまま縦並びの順序になる
    btn.click(fn=process_waka, inputs=[inp, slider], outputs=out)

demo.launch()