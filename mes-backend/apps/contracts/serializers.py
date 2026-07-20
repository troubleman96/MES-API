from rest_framework import serializers

from apps.contracts.models import Contract, Signature


class ContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contract
        fields = ["id", "sub_order", "pdf_url", "generated_at"]


class SignatureSerializer(serializers.ModelSerializer):
    signer_name = serializers.CharField(source="signer.get_full_name", read_only=True)

    class Meta:
        model = Signature
        fields = ["id", "contract", "signer", "signer_name", "signature_image_url", "signed_at"]


class ContractDetailSerializer(serializers.ModelSerializer):
    signatures = SignatureSerializer(many=True, read_only=True)

    class Meta:
        model = Contract
        fields = ["id", "sub_order", "pdf_url", "signatures", "generated_at"]


class SignContractSerializer(serializers.Serializer):
    signature_image_url = serializers.URLField()
