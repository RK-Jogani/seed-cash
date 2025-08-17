from seedcash.models.btc_functions import BitcoinFunctions as bf


class Wallet:
    def __init__(
        self,
        depth,
        father_fingerprint,
        child_index,
        account_chain_code,
        account_key,
        account_public_key,
    ) -> None:

        self.xpriv = bf.xpriv_encode(
            depth, father_fingerprint, child_index, account_chain_code, account_key
        )

        self.xpub = bf.xpub_encode(
            depth,
            father_fingerprint,
            child_index,
            account_chain_code,
            account_public_key,
        )

        self.fingerprint = bf.fingerprint_hex(account_key)

    @property
    def _xpriv(self) -> str:
        return self.xpriv

    @property
    def _xpub(self) -> str:
        return self.xpub

    @property
    def _fingerprint(self) -> str:
        return self.fingerprint
