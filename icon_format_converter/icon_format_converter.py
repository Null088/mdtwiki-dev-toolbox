import subprocess
import re
import time
import sys
import os
import json


#默认设置
default_config = {
    #输出模式 F为[[File:]]格式 P为{{picture}}格式 
    "output_mode":"F",
    #处理模式 N为默认 C为替换模式(仅处理已有格式) RES为恢复模式(将已有格式撤销)
    "processing_mode":"N",
    #是否启用索引以缩短处理用时，仅在数据量极大的情况下有明显效果
    "use_index":True,
    #是否读取文件，开启该模式时无法使用控制台进行输入
    "read_file":False,
    #读取文件的文件名
    "input_file_name":"input_file.txt"
}
#此处赋值仅便于调用
config = default_config

def get_base_dir():
    if getattr(sys, 'frozen', False):
        #如果在打包环境下，则返回exe文件所在的文件夹路径
        return os.path.dirname(sys.executable)
    else:
        #如果在开发环境下，则返回py文件所在的文件夹路径
        return os.path.dirname(os.path.abspath(__file__))
    
def load_config():
    #声明全局变量
    global config
    #构建配置文件路径
    config_path = os.path.join(BASE_DIR, "config.json")

    if not os.path.exists(config_path):
        with open(config_path, "w", encoding="utf-8") as file:
            json.dump(default_config, file, indent=4, ensure_ascii=False)
        ErrorExit("未找到配置文件 config.json ，已重新生成，请确保新 config.json 文件无误后重新运行程序")

    try:
        with open(config_path, "r", encoding="utf-8") as file:
            config = json.load(file)
    except:
        ErrorExit("在读取配置文件 config.json 中的设置时出现了问题（可尝试删除原 config.json ，程序会重新生成的）")


def get_file_path():
    input_file_path = os.path.join(BASE_DIR, config["input_file_name"])
    output_file_path = os.path.join(BASE_DIR, f"{config['input_file_name']}(output).txt")
    return input_file_path, output_file_path

#匹配find_key中的元素是否正确
def match_key(_find_key):
    global skip
    while _find_key != []:
        #获取find_key中最长的字符串
        key_max_len = max(_find_key, key=len)
        #判断是否与text_input对应位置字段相同
        if text_input[i:(i+len(key_max_len))] == key_max_len:
            skip = len(key_max_len)-1
            return transform_format(key_max_len)
        _find_key.remove(key_max_len)
        #如果find_key中的全部元素都不匹配就放弃
    return text_input[i]

#转化成wiki的[[File:]]格式或{{picture}}格式
def transform_format(key,size="18"):
    value = data_dictionary[key].split(".")
    if config["processing_mode"] == "C":
        text_input_end = ""
    else:
        text_input_end = f"[[{key}]]"
    if config["output_mode"] == "F":
        if "planet" in value:
            return f"[[File:{value[0]}-{value[1]}.png|{size}px|link={key}]]{text_input_end}"
        else:
            return f"[[File:{value[0]}-{value[1]}-ui.png|{size}px|link={key}]]{text_input_end}"
    elif config["output_mode"] == "P":
        _text_output = "{{" + f"picture|{key}"
        if size != "18":
            _text_output += f"|size={size}"
        return _text_output + "}}" + f"{text_input_end}"
    else:
        ErrorExit("请检查out_mode的数据是否正确")

#异常退出
def ErrorExit(text_error="异常退出",error_info=0):
    print(text_error, file=sys.stderr)
    input(">按下Enter以关闭窗口")
    sys.exit(error_info)

def main():
    #定义全局变量
    global data_index
    global data_dictionary
    global data_key
    global text_input
    global i
    global skip
    global BASE_DIR

    #获取目录
    BASE_DIR = get_base_dir()
    load_config()
    input_file_path, output_file_path = get_file_path()
    #处理映射表
    data_index = {}
    data_dictionary = {}
    data_key = []
    for data in local_data_list:
        data = data.split(" = ")
        data_key.append(data[1])
        data_dictionary[data[1]]=data[0]
        if config["use_index"] == True:
            key_index = data[1][0]
            #判断data_index是否有对应值，如果有就添加，没有则添加默认值
            if data_index.setdefault(key_index,[data[1]]) != [data[1]]:
                data_index[key_index].append(data[1])
    #控制台主逻辑
    while True:
        if config["read_file"] == False:
            text_input_list = input("输入：")
            
        elif config["read_file"] == True:
            try:
                with open(input_file_path, "r", encoding="utf-8") as file:
                    text_input_list = file.read()
            except:
                ErrorExit(f"在读取文件 {config['input_file_name']} 时发生错误，请检查文件名是否正确")
        else:
            ErrorExit("请检查read_file的数据是否正确")
            return

        start_time = time.perf_counter()
        #正则表达式 按照[[……]]与{{……}}的格式进行分割处理
        text_input_list = [p for p in re.split(r"(\[\[.*?\]\]|\{\{.*?\}\})", text_input_list) if p]
        text_output = ""
        skip = 0

        #主循环 正向映射
        if config["processing_mode"] == "N":
            for text_input in text_input_list:
                #判断是否存在[[……]]或{{……}}的格式，如果存在则不处理直接输出
                if text_input[:2] + text_input[-2:] in ["[[]]", "{{}}"]:
                    text_output += str(text_input)
                else:
                    for i in range(len(text_input)):
                        #跳过已经处理的字符
                        if skip > 0:
                            skip -= 1
                            continue

                        #不使用索引时
                        if config["use_index"] == False:
                            #在data_key(存储了所有的中文名称)中寻找包含text_input[i]的元素
                            find_key = [x for x in data_key if text_input[i] in x]
                        #使用索引时
                        else:
                            if text_input[i] in data_index:
                                #切片复制避免影响索引
                                find_key = data_index[text_input[i]][:]
                            else:
                                find_key = []
                    
                        if find_key != []:
                            text_output += match_key(find_key)
                        else:
                            text_output += text_input[i]

        #替换模式
        elif config["processing_mode"] == "C":
            for text_input in text_input_list:
                #（偷懒）如果包含#就不处理
                if "#" in text_input:
                    text_output += text_input
                    continue
                #将{{picture}}格式转化成[[Flie]]格式
                if config["output_mode"] == "F":
                    if text_input[2:9] == "picture":
                        #按照"{{" "|" "}}" 分割格式
                        key_match = [p for p in re.split(r'\{\{|\||\}\}', text_input) if p][1]
                        #获取"size=……"中的数据
                        size_match = re.search(r'size\s*=\s*([^}|]+)', text_input)
                        if size_match is None:
                            text_output += transform_format(key_match)
                        else:
                            text_output += transform_format(key_match, size_match.group(1))
                    else:
                        text_output += text_input
                #将[[Flie]]格式转化成{{picture}}格式
                elif config["output_mode"] == "P":
                    if text_input[2:7] == "File:":
                        #获取"link=……"中的数据
                        key_match = re.search(r'link=([^|\]]+)', text_input)
                        #获取"……px"中的数据
                        size_match = re.search(r'\|(\d+)px(?=\||\]\]|$)', text_input)
                        text_output += transform_format(key_match.group(1), size_match.group(1))
                    else:
                        text_output += text_input

        #恢复模式
        elif config["processing_mode"] == "RES":
            len_text_input_list = len(text_input_list)
            for i in range(len_text_input_list):
                if skip > 0:
                    skip -= 1
                    continue

                text_input = text_input_list[i]
                #判断是否存在[[……]]或{{……}}的格式，如果存在则进行恢复
                if  text_input[:2] + text_input[-2:] in ["[[]]", "{{}}"]:
                    #（i+1的判断是为避免索引越界）
                    if  i+1 < len_text_input_list and text_input_list[i+1][:2] + text_input_list[i+1][-2:] == "[[]]":
                        skip += 1
                        #将[[File]]/{{picture}}[[……]]中[[……]]的内容添加到text_output
                        text_output += text_input_list[i+1][2:-2]
                    else:
                        #如果首个元素中包含"[["，则认为是[[File]]格式
                        if "[[" in text_input[0]:
                            #使用正则表达式获取"link="后的数据
                            text_output += re.search(r'link=([^|\]]+)', text_input)
                        #否则认为是{{picture}}格式
                        else:
                            #正则表达式 按照"|" "]]" "}}"将文本分割
                            text_input = re.split(r'\||\]\]|\}\}', text_input)
                            text_output += text_input[1]
                else:
                    text_output += text_input
                    
        if config["read_file"] == False:
            print(f"\n{text_output}")
            try:
                subprocess.run("clip", input = text_output.encode("gbk"))
            except:
                print("\n自动复制失败（该功能仅在 Windows下可用）")
            else:
                print("\n已自动复制到剪切板")
        else:
            try:
                with open(output_file_path, "w", encoding="utf-8") as file:
                    file.write(text_output)
            except:
                ErrorExit("\n文件保存失败")
            else:
                print(f"\n文件已保存到 {config['input_file_name']}(output).txt 中")
        end_time = time.perf_counter()
        print(f"处理用时：{end_time-start_time:.6f} 秒")
        print("-"*30)
        if config["read_file"] == True:
            return

#数据
local_data_list = [
    #星球
    "planet.serpulo.name = 塞普罗",
    "planet.erekir.name = 埃里克尔",
    "planet.sun.name = 太阳",
    #区块（塞普罗）
    "sector.impact0078.name = 冲击区 0078",
    "sector.groundZero.name = 零号地区",
    "sector.craters.name = 陨石带",
    "sector.frozenForest.name = 冰冻森林",
    "sector.ruinousShores.name = 遗迹海岸",
    "sector.stainedMountains.name = 绵延群山",
    "sector.desolateRift.name = 荒芜裂谷",
    "sector.nuclearComplex.name = 核裂阵",
    "sector.overgrowth.name = 增生区",
    "sector.tarFields.name = 焦油田",
    "sector.saltFlats.name = 盐碱荒滩",
    "sector.fungalPass.name = 真菌通道",
    "sector.biomassFacility.name = 生物质合成区",
    "sector.windsweptIslands.name = 风吹群岛",
    "sector.extractionOutpost.name = 萃取前哨",
    "sector.facility32m.name = 工业区 32M",
    "sector.taintedWoods.name = 孢染丛林",
    "sector.infestedCanyons.name = 菌疫峡谷",
    "sector.planetaryTerminal.name = 行星发射终端",
    "sector.coastline.name = 边际海湾",
    "sector.navalFortress.name = 海军要塞",
    "sector.polarAerodrome.name = 极地空港",
    "sector.atolls.name = 环礁群岛",
    "sector.testingGrounds.name = 实验禁区",
    "sector.perilousHarbor.name = 险境港",
    "sector.weatheredChannels.name = 风化海峡",
    "sector.fallenVessel.name = 坠舰残骸",
    "sector.mycelialBastion.name = 菌丝堡垒",
    "sector.frontier.name = 边陲哨站",
    "sector.sunkenPier.name = 沉没码头",
    "sector.cruxscape.name = 赤色总部",
    "sector.geothermalStronghold.name = 熔石要塞",
    #区块（埃里克尔）
    "sector.onset.name = 始发地区",
    "sector.aegis.name = 庇护前哨",
    "sector.lake.name = 岩浆湖",
    "sector.intersect.name = 交错丘陵",
    "sector.atlas.name = 风化山脉",
    "sector.split.name = 横断山谷",
    "sector.basin.name = 风蚀盆地",
    "sector.marsh.name = 芳油湿地",
    "sector.peaks.name = 横堑峰峦",
    "sector.ravine.name = 贫瘠峡谷",
    "sector.caldera-erekir.name = 破碎火山",
    "sector.stronghold.name = 晶石要塞",
    "sector.crevice.name = 碳岩裂隙",
    "sector.siege.name = 平行岭谷",
    "sector.crossroads.name = 十字路口",
    "sector.karst.name = 岩溶洞穴",
    "sector.origin.name = 起源",
    #状态
    "status.burning.name = 燃烧",
    "status.freezing.name = 冻结",
    "status.wet.name = 潮湿",
    "status.muddy.name = 泥泞",
    "status.melting.name = 熔化",
    "status.sapped.name = 弱化",
    "status.electrified.name = 麻痹",
    "status.spore-slowed.name = 孢子减速",
    "status.tarred.name = 油浸",
    "status.overdrive.name = 过载",
    "status.overclock.name = 超频",
    "status.shocked.name = 电击",
    "status.blasted.name = 爆炸",
    "status.corroded.name = 腐蚀",
    "status.unmoving.name = 静止",
    "status.boss.name = Boss",
    #物品
    "item.copper.name = 铜",
    "item.lead.name = 铅",
    "item.coal.name = 煤炭",
    "item.graphite.name = 石墨",
    "item.titanium.name = 钛",
    "item.thorium.name = 钍",
    "item.silicon.name = 硅",
    "item.plastanium.name = 塑钢",
    "item.phase-fabric.name = 相织布",
    "item.surge-alloy.name = 巨浪合金",
    "item.spore-pod.name = 孢子荚",
    "item.sand.name = 沙",
    "item.blast-compound.name = 爆炸混合物",
    "item.pyratite.name = 硫化物",
    "item.metaglass.name = 钢化玻璃",
    "item.scrap.name = 废料",
    "item.fissile-matter.name = 裂变产物",
    "item.beryllium.name = 铍",
    "item.tungsten.name = 钨",
    "item.oxide.name = 氧化物",
    "item.carbide.name = 碳化物",
    "item.dormant-cyst.name = 休眠囊肿",
    #液体
    "liquid.water.name = 水",
    "liquid.slag.name = 矿渣",
    "liquid.oil.name = 石油",
    "liquid.cryofluid.name = 冷冻液",
    "liquid.neoplasm.name = 瘤液",
    "liquid.arkycite.name = 芳油",
    "liquid.gallium.name = 镓液",
    "liquid.ozone.name = 臭氧",
    "liquid.hydrogen.name = 氢气",
    "liquid.nitrogen.name = 氮气",
    "liquid.cyanogen.name = 氰气",
    #单位
    "unit.dagger.name = 尖刀",
    "unit.mace.name = 战锤",
    "unit.fortress.name = 堡垒",
    "unit.nova.name = 新星",
    "unit.pulsar.name = 恒星",
    "unit.quasar.name = 耀星",
    "unit.crawler.name = 爬虫",
    "unit.atrax.name = 毒蛛",
    "unit.spiroct.name = 血蛭",
    "unit.arkyid.name = 毒蛊",
    "unit.toxopid.name = 天蝎",
    "unit.flare.name = 星辉",
    "unit.horizon.name = 天垠",
    "unit.zenith.name = 苍穹",
    "unit.antumbra.name = 月影",
    "unit.eclipse.name = 日蚀",
    "unit.mono.name = 独影",
    "unit.poly.name = 幻型",
    "unit.mega.name = 巨像",
    "unit.quad.name = 雷霆",
    "unit.oct.name = 要塞",
    "unit.risso.name = 梭鱼",
    "unit.minke.name = 飞鲨",
    "unit.bryde.name = 戟鲸",
    "unit.sei.name = 蛟龙",
    "unit.omura.name = 海神",
    "unit.retusa.name = 潜螺",
    "unit.oxynoe.name = 电鳗",
    "unit.cyerce.name = 江豚",
    "unit.aegires.name = 玄武",
    "unit.navanax.name = 龙王",
    "unit.alpha.name = 阿尔法",
    "unit.beta.name = 贝塔",
    "unit.gamma.name = 伽马",
    "unit.scepter.name = 权杖",
    "unit.reign.name = 王座",
    "unit.vela.name = 灾星",
    "unit.corvus.name = 死星",
    "unit.stell.name = 围护",
    "unit.locus.name = 循迹",
    "unit.precept.name = 准绳",
    "unit.vanquish.name = 征服",
    "unit.conquer.name = 领主",
    "unit.merui.name = 天守",
    "unit.cleroi.name = 天赐",
    "unit.anthicus.name = 天灾",
    "unit.tecta.name = 天理",
    "unit.collaris.name = 天帝",
    "unit.elude.name = 挣脱",
    "unit.avert.name = 遮蔽",
    "unit.obviate.name = 消散",
    "unit.quell.name = 遏止",
    "unit.disrupt.name = 悲怆",
    "unit.evoke.name = 苏醒",
    "unit.incite.name = 策动",
    "unit.emanate.name = 发散",
    "unit.manifold.name = 货运无人机",
    "unit.assembly-drone.name = 装配无人机",
    "unit.latum.name = 拉图姆",
    "unit.renale.name = 雷纳尔",
    #方块（含建筑）
    "block.parallax.name = 差扰",
    "block.cliff.name = 悬崖",
    "block.sand-boulder.name = 砂岩",
    "block.basalt-boulder.name = 玄武岩石块",
    "block.grass.name = 草地",
    "block.molten-slag.name = 矿渣液",
    "block.pooled-cryofluid.name = 冷冻液(地板)",
    "block.space.name = 太空",
    "block.salt.name = 盐碱地",
    "block.salt-wall.name = 盐墙",
    "block.pebbles.name = 鹅卵石",
    "block.tendrils.name = 卷须",
    "block.sand-wall.name = 沙墙",
    "block.spore-pine.name = 孢子树",
    "block.spore-wall.name = 孢子墙",
    "block.boulder.name = 石块",
    "block.snow-boulder.name = 雪石块",
    "block.snow-pine.name = 雪树",
    "block.shale.name = 页岩地",
    "block.shale-boulder.name = 页岩石块",
    "block.moss.name = 苔藓地",
    "block.shrubs.name = 灌木丛",
    "block.spore-moss.name = 孢子苔藓地",
    "block.shale-wall.name = 页岩墙",
    "block.scrap-wall.name = 废墙",
    "block.scrap-wall-large.name = 大型废墙",
    "block.scrap-wall-huge.name = 巨型废墙",
    "block.scrap-wall-gigantic.name = 超巨型废墙",
    "block.thruster.name = 推进器残骸",
    "block.kiln.name = 窑炉",
    "block.graphite-press.name = 石墨压缩机",
    "block.multi-press.name = 多重压缩机",
    "block.constructing = {0}[lightgray]（建造中）",
    "block.spawn.name = 敌人出生点",
    "block.remove-wall.name = 移除墙体",
    "block.remove-ore.name = 移除矿",
    "block.core-shard.name = 初代核心",
    "block.core-foundation.name = 次代核心",
    "block.core-nucleus.name = 终代核心",
    "block.deep-water.name = 深水",
    "block.shallow-water.name = 水(地板)",
    "block.tainted-water.name = 污水",
    "block.deep-tainted-water.name = 深污水",
    "block.darksand-tainted-water.name = 黑沙污水",
    "block.tar.name = 石油(地板)",
    "block.stone.name = 石头",
    "block.sand-floor.name = 沙子",
    "block.darksand.name = 黑沙",
    "block.ice.name = 冰",
    "block.snow.name = 雪",
    "block.crater-stone.name = 陨石坑",
    "block.sand-water.name = 浅滩",
    "block.darksand-water.name = 黑沙浅滩",
    "block.char.name = 焦土",
    "block.dacite.name = 安山岩",
    "block.rhyolite.name = 流纹岩",
    "block.dacite-wall.name = 安山岩墙",
    "block.dacite-boulder.name = 安山石块",
    "block.ice-snow.name = 冰雪地",
    "block.stone-wall.name = 石墙",
    "block.ice-wall.name = 冰墙",
    "block.snow-wall.name = 雪墙",
    "block.dune-wall.name = 沙丘岩",
    "block.pine.name = 松树",
    "block.dirt.name = 泥土",
    "block.dirt-wall.name = 泥土墙",
    "block.mud.name = 泥巴",
    "block.white-tree-dead.name = 枯萎的白树",
    "block.white-tree.name = 白树",
    "block.spore-cluster.name = 孢子簇",
    "block.metal-floor.name = 金属地板 1",
    "block.metal-floor-2.name = 金属地板 2",
    "block.metal-floor-3.name = 金属地板 3",
    "block.metal-floor-4.name = 金属地板 4",
    "block.metal-floor-5.name = 金属地板 5",
    "block.metal-floor-damaged.name = 损坏的金属地板",
    "block.metal-tiles-1.name = 金属地基 1",
    "block.metal-tiles-2.name = 金属地基 2",
    "block.metal-tiles-3.name = 金属地基 3",
    "block.metal-tiles-4.name = 金属地基 4",
    "block.metal-tiles-5.name = 金属地基 5",
    "block.metal-tiles-6.name = 金属地基 6",
    "block.metal-tiles-7.name = 金属地基 7",
    "block.metal-tiles-8.name = 金属地基 8",
    "block.metal-tiles-9.name = 金属地基 9",
    "block.metal-tiles-10.name = 金属地基 10",
    "block.metal-tiles-11.name = 金属地基 11",
    "block.metal-tiles-12.name = 金属地基 12",
    "block.metal-tiles-13.name = 金属地基 13",
    "block.metal-wall-1.name = 金属墙 1",
    "block.metal-wall-2.name = 金属墙 2",
    "block.metal-wall-3.name = 金属墙 3",
    "block.colored-floor.name = 染色地板",
    "block.colored-wall.name = 染色墙壁",
    "block.character-overlay.name = 标识贴片",
    "block.character-overlay-white.name = 标识贴片 (白色)",
    "block.rune-overlay.name = 符文贴片",
    "block.rune-overlay-crux.name = 符文贴片 （红队）",
    "block.dark-panel-1.name = 暗面板 1",
    "block.dark-panel-2.name = 暗面板 2",
    "block.dark-panel-3.name = 暗面板 3",
    "block.dark-panel-4.name = 暗面板 4",
    "block.dark-panel-5.name = 暗面板 5",
    "block.dark-panel-6.name = 暗面板 6",
    "block.dark-metal.name = 暗金属",
    "block.basalt.name = 玄武岩",
    "block.hotrock.name = 灼热岩石",
    "block.magmarock.name = 熔融岩石",
    "block.copper-wall.name = 铜墙",
    "block.copper-wall-large.name = 大型铜墙",
    "block.titanium-wall.name = 钛墙",
    "block.titanium-wall-large.name = 大型钛墙",
    "block.plastanium-wall.name = 塑钢墙",
    "block.plastanium-wall-large.name = 大型塑钢墙",
    "block.phase-wall.name = 相织布墙",
    "block.phase-wall-large.name = 大型相织布墙",
    "block.thorium-wall.name = 钍墙",
    "block.thorium-wall-large.name = 大型钍墙",
    "block.door.name = 门",
    "block.door-large.name = 大门",
    "block.duo.name = 双管",
    "block.scorch.name = 火焰",
    "block.scatter.name = 分裂",
    "block.hail.name = 冰雹",
    "block.lancer.name = 蓝瑟",
    "block.conveyor.name = 传送带",
    "block.titanium-conveyor.name = 钛传送带",
    "block.plastanium-conveyor.name = 塑钢传送带",
    "block.armored-conveyor.name = 装甲传送带",
    "block.junction.name = 交叉器",
    "block.router.name = 路由器",
    "block.distributor.name = 分配器",
    "block.sorter.name = 分类器",
    "block.inverted-sorter.name = 反向分类器",
    "block.message.name = 信息板",
    "block.reinforced-message.name = 强化信息板",
    "block.world-message.name = 世界信息板",
    "block.world-switch.name = 世界开关",
    "block.illuminator.name = 照明器",
    "block.overflow-gate.name = 溢流门",
    "block.underflow-gate.name = 反向溢流门",
    "block.silicon-smelter.name = 硅冶炼厂",
    "block.phase-weaver.name = 相织布编织器",
    "block.pulverizer.name = 粉碎机",
    "block.cryofluid-mixer.name = 冷冻液混合器",
    "block.melter.name = 熔炉",
    "block.incinerator.name = 焚化炉",
    "block.spore-press.name = 孢子压缩机",
    "block.separator.name = 分离机",
    "block.coal-centrifuge.name = 煤炭离心机",
    "block.power-node.name = 电力节点",
    "block.power-node-large.name = 大型电力节点",
    "block.surge-tower.name = 巨浪电力塔",
    "block.diode.name = 二极管",
    "block.battery.name = 电池",
    "block.battery-large.name = 大型电池",
    "block.combustion-generator.name = 火力发电机",
    "block.steam-generator.name = 涡轮发电机",
    "block.differential-generator.name = 温差发电机",
    "block.impact-reactor.name = 冲击反应堆",
    "block.mechanical-drill.name = 机械钻头",
    "block.pneumatic-drill.name = 气动钻头",
    "block.laser-drill.name = 激光钻头",
    "block.water-extractor.name = 抽水机",
    "block.cultivator.name = 培养机",
    "block.conduit.name = 导管",
    "block.mechanical-pump.name = 机械泵",
    "block.item-source.name = 物品源",
    "block.item-void.name = 物品黑洞",
    "block.liquid-source.name = 液体源",
    "block.liquid-void.name = 液体黑洞",
    "block.power-void.name = 电力黑洞",
    "block.power-source.name = 电力源",
    "block.unloader.name = 装卸器",
    "block.vault.name = 仓库",
    "block.wave.name = 波浪",
    "block.tsunami.name = 海啸",
    "block.swarmer.name = 蜂群",
    "block.salvo.name = 齐射",
    "block.ripple.name = 浪涌",
    "block.phase-conveyor.name = 相织布传送带桥",
    "block.bridge-conveyor.name = 传送带桥",
    "block.plastanium-compressor.name = 塑钢压缩机",
    "block.pyratite-mixer.name = 硫化物混合器",
    "block.blast-mixer.name = 爆炸物混合器",
    "block.solar-panel.name = 太阳能板",
    "block.solar-panel-large.name = 大型太阳能板",
    "block.oil-extractor.name = 石油钻井",
    "block.repair-point.name = 维修点",
    "block.repair-turret.name = 维修塔",
    "block.pulse-conduit.name = 脉冲导管",
    "block.plated-conduit.name = 电镀导管",
    "block.phase-conduit.name = 相织布导管桥",
    "block.liquid-router.name = 流体路由器",
    "block.liquid-tank.name = 流体储罐",
    "block.liquid-container.name = 流体容器",
    "block.liquid-junction.name = 流体交叉器",
    "block.bridge-conduit.name = 导管桥",
    "block.rotary-pump.name = 回转泵",
    "block.thorium-reactor.name = 钍反应堆",
    "block.mass-driver.name = 质量驱动器",
    "block.blast-drill.name = 爆破钻头",
    "block.impulse-pump.name = 脉冲泵",
    "block.thermal-generator.name = 热能发电机",
    "block.surge-smelter.name = 合金冶炼厂",
    "block.mender.name = 修理器",
    "block.mend-projector.name = 修理投影",
    "block.surge-wall.name = 合金墙",
    "block.surge-wall-large.name = 大型合金墙",
    "block.cyclone.name = 气旋",
    "block.fuse.name = 雷光",
    "block.shock-mine.name = 脉冲地雷",
    "block.overdrive-projector.name = 超速投影",
    "block.force-projector.name = 力墙投影",
    "block.arc.name = 电弧",
    "block.rtg-generator.name = RTG 发电机",
    "block.spectre.name = 幽灵",
    "block.meltdown.name = 熔毁",
    "block.foreshadow.name = 厄兆",
    "block.container.name = 容器",
    "block.launch-pad.name = 发射台（旧版）",
    "block.advanced-launch-pad.name = 发射台",
    "block.landing-pad.name = 接收台",
    "block.segment.name = 裂解",
    "block.ground-factory.name = 陆军工厂",
    "block.air-factory.name = 空军工厂",
    "block.naval-factory.name = 海军工厂",
    "block.additive-reconstructor.name = 数增级单位重构工厂",
    "block.multiplicative-reconstructor.name = 倍乘级单位重构工厂",
    "block.exponential-reconstructor.name = 多幂级单位重构工厂",
    "block.tetrative-reconstructor.name = 无量级单位重构工厂",
    "block.payload-conveyor.name = 载荷传送带",
    "block.payload-router.name = 载荷路由器",
    "block.duct.name = 物品管道",
    "block.duct-router.name = 物品管道路由器",
    "block.duct-bridge.name = 物品管道桥",
    "block.large-payload-mass-driver.name = 大型载荷质量驱动器",
    "block.payload-void.name = 载荷黑洞",
    "block.payload-source.name = 载荷源",
    "block.disassembler.name = 解离机",
    "block.silicon-crucible.name = 热能坩埚",
    "block.overdrive-dome.name = 超速穹顶",
    "block.interplanetary-accelerator.name = 行星际加速器",
    "block.constructor.name = 构筑器",
    "block.large-constructor.name = 大型构筑器",
    "block.deconstructor.name = 大型解构器",
    "block.payload-loader.name = 载荷装载器",
    "block.payload-unloader.name = 载荷卸载器",
    "block.heat-source.name = 热量源",
    #Erekir 方块
    "block.empty.name = 空",
    "block.rhyolite-crater.name = 流纹岩坑",
    "block.rough-rhyolite.name = 粗糙流纹岩",
    "block.regolith.name = 风化岩",
    "block.yellow-stone.name = 黄石",
    "block.carbon-stone.name = 碳石",
    "block.ferric-stone.name = 铁石",
    "block.ferric-craters.name = 铁陨石坑",
    "block.beryllic-stone.name = 铍石",
    "block.crystalline-stone.name = 晶石",
    "block.crystal-floor.name = 晶石地板",
    "block.yellow-stone-plates.name = 黄石地板",
    "block.red-stone.name = 红石",
    "block.dense-red-stone.name = 高密红石",
    "block.red-ice.name = 红冰",
    "block.arkycite-floor.name = 芳油(地板)",
    "block.arkyic-stone.name = 芳石",
    "block.rhyolite-vent.name = 流纹石喷口",
    "block.carbon-vent.name = 碳石喷口",
    "block.arkyic-vent.name = 芳石喷口",
    "block.yellow-stone-vent.name = 黄石喷口",
    "block.red-stone-vent.name = 红石喷口",
    "block.crystalline-vent.name = 晶石喷口",
    "block.stone-vent.name = 岩石喷口",
    "block.basalt-vent.name = 玄武岩喷口",
    "block.redmat.name = 红地垫",
    "block.bluemat.name = 蓝地垫",
    "block.core-zone.name = 核心区",
    "block.regolith-wall.name = 风化墙",
    "block.yellow-stone-wall.name = 黄石墙",
    "block.rhyolite-wall.name = 流纹岩墙",
    "block.carbon-wall.name = 碳石墙",
    "block.ferric-stone-wall.name = 铁石墙",
    "block.beryllic-stone-wall.name = 铍石墙",
    "block.arkyic-wall.name = 芳石墙",
    "block.crystalline-stone-wall.name = 晶石墙",
    "block.red-ice-wall.name = 红冰墙",
    "block.red-stone-wall.name = 红石墙",
    "block.red-diamond-wall.name = 红钻墙",
    "block.redweed.name = 赤藻",
    "block.pur-bush.name = 紫灌木丛",
    "block.yellowcoral.name = 黄珊瑚",
    "block.carbon-boulder.name = 碳石块",
    "block.ferric-boulder.name = 铁石块",
    "block.beryllic-boulder.name = 铍石块",
    "block.yellow-stone-boulder.name = 黄石块",
    "block.arkyic-boulder.name = 芳石块",
    "block.crystal-cluster.name = 水晶簇",
    "block.vibrant-crystal-cluster.name = 鲜艳水晶簇",
    "block.crystal-blocks.name = 风化晶体",
    "block.crystal-orbs.name = 晶石球",
    "block.crystalline-boulder.name = 晶石块",
    "block.red-ice-boulder.name = 红冰石块",
    "block.rhyolite-boulder.name = 流纹石块",
    "block.red-stone-boulder.name = 红石块",
    "block.graphitic-wall.name = 石墨墙",
    "block.silicon-arc-furnace.name = 电弧硅炉",
    "block.electrolyzer.name = 电解机",
    "block.atmospheric-concentrator.name = 大气收集器",
    "block.oxidation-chamber.name = 氧化室",
    "block.electric-heater.name = 电制热机",
    "block.slag-heater.name = 矿渣制热机",
    "block.phase-heater.name = 相织制热机",
    "block.heat-redirector.name = 热量传输机",
    "block.small-heat-redirector.name = 小型热量传输机",
    "block.heat-router.name = 热量路由器",
    "block.slag-incinerator.name = 矿渣焚化炉",
    "block.carbide-crucible.name = 碳化物坩埚",
    "block.slag-centrifuge.name = 矿渣离心机",
    "block.surge-crucible.name = 合金坩埚",
    "block.cyanogen-synthesizer.name = 氰合成机",
    "block.phase-synthesizer.name = 相织布合成机",
    "block.heat-reactor.name = 热量反应堆",
    "block.beryllium-wall.name = 铍墙",
    "block.beryllium-wall-large.name = 大型铍墙",
    "block.tungsten-wall.name = 钨墙",
    "block.tungsten-wall-large.name = 大型钨墙",
    "block.blast-door.name = 防爆闸门",
    "block.carbide-wall.name = 碳化物墙",
    "block.carbide-wall-large.name = 大型碳化物墙",
    "block.reinforced-surge-wall.name = 强化合金墙",
    "block.reinforced-surge-wall-large.name = 大型强化合金墙",
    "block.shielded-wall.name = 盾墙",
    "block.radar.name = 雷达",
    "block.build-tower.name = 建造塔",
    "block.regen-projector.name = 再生投影器",
    "block.shockwave-tower.name = 震爆塔",
    "block.shield-projector.name = 护盾投影器",
    "block.large-shield-projector.name = 大型护盾投影器",
    "block.armored-duct.name = 装甲管道",
    "block.overflow-duct.name = 溢流管道",
    "block.underflow-duct.name = 反向溢流管",
    "block.duct-unloader.name = 管道装卸器",
    "block.surge-conveyor.name = 合金传送带",
    "block.surge-router.name = 合金路由器",
    "block.unit-cargo-loader.name = 单位物流装载器",
    "block.unit-cargo-unload-point.name = 单位物流卸载点",
    "block.reinforced-pump.name = 强化泵",
    "block.reinforced-conduit.name = 强化导管",
    "block.reinforced-liquid-junction.name = 强化流体交叉器",
    "block.reinforced-bridge-conduit.name = 强化流体带桥",
    "block.reinforced-liquid-router.name = 强化流体路由器",
    "block.reinforced-liquid-container.name = 强化流体容器",
    "block.reinforced-liquid-tank.name = 强化流体储罐",
    "block.beam-node.name = 激光节点",
    "block.beam-tower.name = 激光塔",
    "block.beam-link.name = 激光连接器",
    "block.turbine-condenser.name = 涡轮冷凝器",
    "block.chemical-combustion-chamber.name = 化学燃烧室",
    "block.pyrolysis-generator.name = 热解发生器",
    "block.vent-condenser.name = 排气冷凝器",
    "block.cliff-crusher.name = 墙壁粉碎机",
    "block.large-cliff-crusher.name = 高级墙壁粉碎机",
    "block.plasma-bore.name = 等离子钻机",
    "block.large-plasma-bore.name = 高级等离子钻机",
    "block.impact-drill.name = 冲击钻头",
    "block.eruption-drill.name = 爆裂钻头",
    "block.core-bastion.name = 城堡核心",
    "block.core-citadel.name = 堡垒核心",
    "block.core-acropolis.name = 卫城核心",
    "block.reinforced-container.name = 强化容器",
    "block.reinforced-vault.name = 强化仓库",
    "block.breach.name = 撕裂",
    "block.sublimate.name = 升华",
    "block.titan.name = 泰坦",
    "block.disperse.name = 驱离",
    "block.afflict.name = 劫难",
    "block.lustre.name = 光辉",
    "block.scathe.name = 创伤",
    "block.tank-refabricator.name = 坦克重构厂",
    "block.mech-refabricator.name = 机甲重构厂",
    "block.ship-refabricator.name = 飞船重构厂",
    "block.tank-assembler.name = 坦克组装厂",
    "block.ship-assembler.name = 飞船组装厂",
    "block.mech-assembler.name = 机甲组装厂",
    "block.reinforced-payload-conveyor.name = 强化载荷传送带",
    "block.reinforced-payload-router.name = 强化载荷路由器",
    "block.payload-mass-driver.name = 载荷质量驱动器",
    "block.small-deconstructor.name = 解构器",
    "block.canvas.name = 画板",
    "block.world-processor.name = 世界处理器",
    "block.world-cell.name = 世界内存元",
    "block.tank-fabricator.name = 坦克制造厂",
    "block.mech-fabricator.name = 机甲制造厂",
    "block.ship-fabricator.name = 飞船制造厂",
    "block.prime-refabricator.name = 高级再重构工厂",
    "block.unit-repair-tower.name = 单位维修塔",
    "block.diffuse.name = 扩散",
    "block.basic-assembler-module.name = 基本装配厂模块",
    "block.smite.name = 天谴",
    "block.malign.name = 魔灵",
    "block.flux-reactor.name = 通量反应堆",
    "block.neoplasia-reactor.name = 瘤变反应堆",
    #逻辑
    "block.switch.name = 开关",
    "block.micro-processor.name = 微型处理器",
    "block.logic-processor.name = 逻辑处理器",
    "block.hyper-processor.name = 超核处理器",
    "block.logic-display.name = 逻辑显示屏",
    "block.large-logic-display.name = 大型逻辑显示屏",
    "block.tile-logic-display.name = 逻辑显示单元",
    "block.memory-cell.name = 内存元",
    "block.memory-bank.name = 内存库",
    #矿石（部分与方块重复，但保留原键名）
    "block.ore-copper = 铜矿",
    "block.ore-lead = 铅矿",
    "block.ore-scrap = 废料矿",
    "block.ore-coal = 煤炭矿",
    "block.ore-titanium = 钛矿",
    "block.ore-thorium = 钍矿",
    "block.ore-beryllium = 铍矿",
    "block.ore-tungsten = 钨矿",
    "block.ore-crystal-thorium = 钍矿（埃）",
    "block.ore-wall-thorium = 钍（墙）",
    "block.ore-wall-beryllium = 铍（墙）",
    "block.ore-wall-graphite = 石墨（墙）",
    "block.ore-wall-tungsten = 钨（墙）"
]

#执行程序
if __name__ == "__main__":
    main()
