from django.utils.crypto import salted_hmac


def code_pour_livraison(reference):
    """Calcule le code de remise à six chiffres associé à la commande."""
    empreinte = salted_hmac(
        "sharp_sharp.livraisons.code_remise.v1",
        str(reference),
        algorithm="sha256",
    ).hexdigest()

    return f"{int(empreinte, 16) % 1_000_000:06d}"