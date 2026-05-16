from src.cricbuzz_points import parse_points_table


def test_parse_cricbuzz_points_table():
    html = """
    <div class="text-xs">RCB<!-- --> </div></a></div><div class="flex justify-center items-center">12</div><div class="flex justify-center items-center">8</div><div class="flex justify-center items-center">4</div><div class="flex justify-center items-center">0</div><div class="flex justify-center items-center">16</div><div class="flex justify-center items-center">+1.053</div>
    <div class="text-xs">GT<!-- --> </div></a></div><div class="flex justify-center items-center">12</div><div class="flex justify-center items-center">8</div><div class="flex justify-center items-center">4</div><div class="flex justify-center items-center">0</div><div class="flex justify-center items-center">16</div><div class="flex justify-center items-center">+0.551</div>
    <div class="text-xs">SRH<!-- --> </div></a></div><div class="flex justify-center items-center">12</div><div class="flex justify-center items-center">7</div><div class="flex justify-center items-center">5</div><div class="flex justify-center items-center">0</div><div class="flex justify-center items-center">14</div><div class="flex justify-center items-center">+0.331</div>
    <div class="text-xs">PBKS<!-- --> </div></a></div><div class="flex justify-center items-center">12</div><div class="flex justify-center items-center">6</div><div class="flex justify-center items-center">5</div><div class="flex justify-center items-center">1</div><div class="flex justify-center items-center">13</div><div class="flex justify-center items-center">+0.355</div>
    <div class="text-xs">RR<!-- --> </div></a></div><div class="flex justify-center items-center">11</div><div class="flex justify-center items-center">6</div><div class="flex justify-center items-center">5</div><div class="flex justify-center items-center">0</div><div class="flex justify-center items-center">12</div><div class="flex justify-center items-center">+0.082</div>
    <div class="text-xs">CSK<!-- --> </div></a></div><div class="flex justify-center items-center">12</div><div class="flex justify-center items-center">6</div><div class="flex justify-center items-center">6</div><div class="flex justify-center items-center">0</div><div class="flex justify-center items-center">12</div><div class="flex justify-center items-center">+0.027</div>
    <div class="text-xs">DC<!-- --> </div></a></div><div class="flex justify-center items-center">12</div><div class="flex justify-center items-center">5</div><div class="flex justify-center items-center">7</div><div class="flex justify-center items-center">0</div><div class="flex justify-center items-center">10</div><div class="flex justify-center items-center">-0.993</div>
    <div class="text-xs">KKR<!-- --> </div></a></div><div class="flex justify-center items-center">11</div><div class="flex justify-center items-center">4</div><div class="flex justify-center items-center">6</div><div class="flex justify-center items-center">1</div><div class="flex justify-center items-center">9</div><div class="flex justify-center items-center">-0.198</div>
    <div class="text-xs">MI (E)<!-- --> </div></a></div><div class="flex justify-center items-center">12</div><div class="flex justify-center items-center">4</div><div class="flex justify-center items-center">8</div><div class="flex justify-center items-center">0</div><div class="flex justify-center items-center">8</div><div class="flex justify-center items-center">-0.504</div>
    <div class="text-xs">LSG (E)<!-- --> </div></a></div><div class="flex justify-center items-center">12</div><div class="flex justify-center items-center">4</div><div class="flex justify-center items-center">8</div><div class="flex justify-center items-center">0</div><div class="flex justify-center items-center">8</div><div class="flex justify-center items-center">-0.701</div>
    """
    table = parse_points_table(html, snapshot_id="test")
    assert len(table) == 10
    assert table.iloc[0]["team"] == "Royal Challengers Bengaluru"
    assert table.iloc[0]["points"] == 16
    assert table.iloc[-1]["team"] == "Lucknow Super Giants"
