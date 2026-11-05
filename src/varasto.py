class Varasto:
    def __init__(self, tilavuus, alku_saldo = 0):
        self.tilavuus = self.alusta_tilavuus(tilavuus)
        self.saldo = self.alusta_saldo(tilavuus, alku_saldo)

    def alusta_tilavuus(self, tilavuus):
        # virheellinen tilavuus nollataan
        return tilavuus if tilavuus > 0.0 else 0.0

    def alusta_saldo(self, tilavuus, alku_saldo):
        if alku_saldo < 0.0:
            # virheellinen, nollataan
            return 0.0
        # täyteen ja ylimäärä hukkaan!
        return min(alku_saldo, tilavuus)

    def paljonko_mahtuu(self):
        return self.tilavuus - self.saldo

    def lisaa_varastoon(self, maara):
        if maara < 0:
            return
        if maara <= self.paljonko_mahtuu():
            self.saldo = self.saldo + maara
        else:
            self.saldo = self.tilavuus

    def ota_varastosta(self, maara):
        if maara < 0:
            return 0.0
        if maara > self.saldo:
            kaikki_mita_voidaan = self.saldo
            self.saldo = 0.0

            return kaikki_mita_voidaan

        self.saldo = self.saldo - maara

        return maara

    def __str__(self):
        return f"saldo = {self.saldo}, vielä tilaa {self.paljonko_mahtuu()}"
