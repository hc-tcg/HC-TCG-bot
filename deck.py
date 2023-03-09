#Everything to do with deck handling, by ProfNinja

cards = {
   "stressmonster101_rare":3,
   "mumbojumbo_rare":3,
   "grian_rare":3,
   
   
   "hypnotizd_rare":2,
   "tinfoilchef_rare":2,
   "tangotek_common":2,
   "xisumavoid_rare":2,
   "ethoslab_rare":2,
   "impulsesv_rare":2,
   "ethoslab_ultra_rare":2,
   "pearlescentmoon_rare":2,
   
   
   "clock":2,
   "tnt":2,
   "fishing_rod":2,
   "flint_&_steel":2,
   "chest":2,
   "netherite_armor":2,
   "iron_armor":2,
   "bow":2,
   "lead":2,


   "tinfoilchef_common":1,   
   "joehills_rare":1,
   "geminitay_rare":1,
   "tinfoilchef_ultra_rare":1,
   "docm77_rare":1,
   "welsknight_rare":1,
   "xisumavoid_common":1,
   "goodtimeswithscar_common":1,
   "falsesymmetry_rare":1,
   "zombiecleo_rare":1,
   "cubfan135_rare":1,
   "ijevin_rare":1,
   "iskall85_common":1,
   "geminitay_common":1,
   "rendog_rare":1,
   
   
   "diamond_armor":1,
   "instant_health_ii":1,
   "chorus_fruit":1,
   "curse_of_vanishing":1,
   "golden_apple":1,
   "composter":1,
   "netherite_sword":1,
   "lava_bucket":1,
   "splash_potion_of_poison":1,


   "item_prankster_rare":1,
   "item_miner_rare":1,
   "item_redstone_rare":1,
   "item_speedrunner_rare":1,
   "item_terraform_rare":1,
   "item_farm_rare":1,
   "item_pvp_rare":1,
   "item_builder_rare":1,
   "item_balanced_rare":1,
   "item_explorer_rare":1,
   
   "instant_health":0,
   "golden_axe":0,
   "totem":0,
   "splash_potion_of_healing":0,
   "fortune":0,
   "efficiency":0,
   "iron_sword":0,
   "crossbow":0,
   "water_bucket":0,
   "diamond_sword":0,
   "milk_bucket":0,
   "curse_of_binding":0,
   "emerald":0,
   "gold_armor":0,
   "wolf":0,
   "thorns":0,
   "looting":0,
   "knockback":0,
   "shield":0,
   "mending":0,
   "bed":0,
   "invisibility_potion":0,
   "spyglass":0,
   "loyalty":0,
   
   
   "mumbojumbo_common":0,
   "tangotek_rare":0,
   "welsknight_common":0,
   "iskall85_rare":0,
   "keralis_rare":0,
   "xbcrafted_common":0,
   "vintagebeef_rare":0,
   "bdoubleo100_common":0,
   "docm77_common":0,
   "impulsesv_common":0,
   "falsesymmetry_common":0,
   "grian_common":0,
   "hypnotizd_common":0,
   "rendog_common":0,
   "zedaphplays_rare":0,
   "zedaphplays_common":0,
   "stressmonster101_common":0,
   "pearlescentmoon_common":0,
   "ijevin_common":0,
   "goodtimeswithscar_rare":0,
   "zombiecleo_common":0,
   "bdoubleo100_rare":0,
   "ethoslab_common":0,
   "joehills_common":0,
   "xbcrafted_rare":0,
   "cubfan135_common":0,
   "keralis_common":0,
   "vintagebeef_common":0,
   "vintagebeef_ultra_rare":0,
   
   
   "item_prankster_common":0,
   "item_miner_common":0,
   "item_redstone_common":0,
   "item_terraform_common":0,
   "item_farm_common":0,
   "item_speedrunner_common":0,
   "item_builder_common":0,
   "item_pvp_common":0,
   "item_balanced_common":0,
   "item_explorer_common":0
}

universe=["bdoubleo100_common","bdoubleo100_rare","bed","bow","chest","chorus_fruit","clock","composter","crossbow","cubfan135_common","cubfan135_rare","curse_of_binding","curse_of_vanishing","diamond_armor","diamond_sword","docm77_common","docm77_rare","efficiency","emerald","ethoslab_common","ethoslab_rare","ethoslab_ultra_rare","falsesymmetry_common","falsesymmetry_rare","fishing_rod","flint_&_steel","fortune","geminitay_common","geminitay_rare","gold_armor","golden_apple","golden_axe","goodtimeswithscar_common","goodtimeswithscar_rare","grian_common","grian_rare","hypnotizd_common","hypnotizd_rare","ijevin_common","ijevin_rare","impulsesv_common","impulsesv_rare","instant_health","instant_health_ii","invisibility_potion","iron_armor","iron_sword","iskall85_common","iskall85_rare","item_balanced_common","item_balanced_rare","item_builder_common","item_builder_rare","item_explorer_common","item_explorer_rare","item_farm_common","item_farm_rare","item_miner_common","item_miner_rare","item_prankster_common","item_prankster_rare","item_pvp_common","item_pvp_rare","item_redstone_common","item_redstone_rare","item_speedrunner_common","item_speedrunner_rare","item_terraform_common","item_terraform_rare","joehills_common","joehills_rare","keralis_common","keralis_rare","knockback","lava_bucket","lead","looting","loyalty","mending","milk_bucket","mumbojumbo_common","mumbojumbo_rare","netherite_armor","netherite_sword","pearlescentmoon_common","pearlescentmoon_rare","rendog_common","rendog_rare","shield","splash_potion_of_healing","splash_potion_of_poison","spyglass","stressmonster101_common","stressmonster101_rare","tangotek_common","tangotek_rare","thorns","tinfoilchef_common","tinfoilchef_rare","tinfoilchef_ultra_rare","tnt","totem","vintagebeef_common","vintagebeef_rare","vintagebeef_ultra_rare","water_bucket","welsknight_common","welsknight_rare","wolf","xbcrafted_common","xbcrafted_rare","xisumavoid_common","xisumavoid_rare","zedaphplays_common","zedaphplays_rare","zombiecleo_common", "zombiecleo_rare"]

import base64

def hashToDeck(dhsh, universe):
    iarr=list(base64.b64decode(dhsh))
    deck=[]
    for idx in iarr:
        deck.append(universe[idx])
    return deck

def hashToStars(dhsh):
    global universe, cards
    deck = hashToDeck(dhsh, universe)
    stars = 0
    for c in deck:
        stars += cards[c]
    return stars
