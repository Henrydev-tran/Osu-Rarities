def Calculate_Rarity(sr):
    rarity = 0
    newsr = str(sr)

    if not "." in newsr:
        newsr += ".00"
        
    split_sr = str(newsr).split(".")
    basic_sr = int(split_sr[0])
    decimals = split_sr[1]
    decimals += "00"
    
    if basic_sr == 1:
        rarity += 2
    elif basic_sr == 2:
        rarity += 7
    elif basic_sr == 3:
        rarity += 25
    elif basic_sr == 4:
        rarity += 100
    elif basic_sr == 5:
        rarity += 300
    elif basic_sr == 6:
        rarity += 1000
    elif basic_sr == 7:
        rarity += 5000
    elif basic_sr == 8:
        rarity += 30000
    elif basic_sr == 9:
        rarity += 250000
    elif basic_sr == 10:
        rarity += 1500000
    elif basic_sr == 11:
        rarity += 6000000
    elif basic_sr == 12:
        rarity += 20000000
    elif basic_sr == 13:
        rarity += 750000000
    elif basic_sr == 14:
        rarity += 10000000000
    elif basic_sr >= 15:
        rarity += 75000000000
    

    buff1 = int(decimals[0])
    buff2 = int(decimals[1]) / 10

    rarity += ((buff1+buff2)/4) * rarity

    return round(rarity)

