from . import models

from django.http import HttpResponse
from django.shortcuts import render, redirect, reverse
from django.views.generic import ListView, DetailView
from django.views import View
from django.contrib import messages
from produto.models import Variacao
from utils import utils


class DispatchLoginRequired(View):
    def dispatch(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return redirect('perfil:criar')
        return super().dispatch(*args, **kwargs)


class Pagar(DispatchLoginRequired, DetailView):
    template_name = 'pedido/pagar.html'
    model = models.Pedido
    pk_url_kwarg = 'pk'
    context_object_name = 'pedido'

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        qs = qs.filter(usuario=self.request.user)
        return qs


class SalvarPedido(View):
    template_name = 'pedido/pagar.html'

    def get(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            messages.error(
                self.request,
                'Você precisa está logado.'
            )
            return redirect('perfil:criar')
        if not self.request.session.get('carrinho'):
            messages.error(
                self.request,
                'Carrinho vazio.'
            )
            return redirect('produto:lista')
        carrinho = self.request.session.get('carrinho')
        carrinho_variacao_ids = [v for v in carrinho]
        bd_variacao = Variacao.objects.select_related(
            'produto').filter(id__in=carrinho_variacao_ids)
        for variacao in bd_variacao:
            vid = str(variacao.id)
            error_msg_estoque = ''
            estoque = variacao.estoque
            qtd_carrinho = carrinho[vid]['quantidade']
            preco_unitario = carrinho[vid]['preco_unitario']
            preco_unitario_promo = carrinho[vid]['preco_unitario_promocional']
            if estoque < qtd_carrinho:
                carrinho[vid]['quantidade'] = estoque
                carrinho[vid]['preco_quantitativo'] = estoque * preco_unitario
                carrinho[vid]['preco_quantitativo_promocional'] = estoque * \
                    preco_unitario_promo

                error_msg_estoque = 'Estoque insuficiente para alguns produtos do seu carrinho.'
                'Reduzimos a quantidade desses produtos. Por favor verifique'
                'quais produtos foram afetados a seguir'
            if error_msg_estoque:
                messages.error(
                    self.request,
                    error_msg_estoque
                )
                self.request.session.save()
                return redirect('produto:carrinho')
        qtd_total_carrinho = utils.cart_total_qtd(carrinho)
        valor_total_carrinho = utils.cart_totals(carrinho)

        pedido = models.Pedido(
            usuario=self.request.user,
            total=valor_total_carrinho,
            qtd_total=qtd_total_carrinho,
            status='C'
        )
        pedido.save()
        models.ItemPedido.objects.bulk_create(
            [
                models.ItemPedido(
                    pedido=pedido,
                    produto=v['produto_nome'],
                    produto_id=v['produto_id'],
                    variacao=v['variacao_nome'],
                    variacao_id=v['variacao_id'],
                    preco=v['preco_quantitativo'],
                    preco_promocional=v['preco_quantitativo_promocional'],
                    quantidade=v['quantidade'],
                    imagem=v['imagem'],
                )for v in carrinho.values()
            ]
        )

        del self.request.session['carrinho']
        return redirect(
            reverse(
                'pedido:pagar',
                kwargs={
                    'pk': pedido.pk
                }
            )
        )


class Detalhe(View):
    def get(self, *args, **kwargs):
        return HttpResponse('pagar')


class Lista(View):
    def get(self, *args, **kwargs):
        return HttpResponse('lista')
