# Conexão WhatsApp Cloud API

A conexão **WhatsApp Cloud API** é o método oficial da Meta para vincular seu número de WhatsApp Business à Persua. Esse processo garante comunicação segura entre a API e o WhatsApp Business, e é essencial quando seu número não é elegível para conexão via QR Code.

:::success
**Pré-requisitos**

- **Número disponível**, um telefone cadastrado no **WhatsApp Business**
- **Desconexão do aplicativo**, o número não pode estar conectado ao aplicativo WhatsApp no celular. Se estiver, desconecte a conta antes de iniciar
- **Portfólio Empresarial**, um Gerenciador de Negócios (Meta Business Suite) configurado
- **Perfil Administrador**, ser admin na Persua e no Facebook
- **Recebimento de código**, ter acesso ao número para receber o código de verificação via SMS ou ligação telefônica
:::

---

## Passo 1. Iniciando a integração

No menu superior da plataforma, clique em **Ajustes** e depois em **Conta**.

[PRINT 01 → arraste: assets/conexao-whatsapp-cloud-api/print-01.png]

Clique na aba **Canais de Atendimento** e em seguida no botão de adição **(+)**. Navegue até **WhatsApp Cloud API** e selecione **Cloud Meta**.

[PRINT 02 → arraste: assets/conexao-whatsapp-cloud-api/print-02.png]

---

## Passo 2. Configuração do número

Selecione a opção **Conectar novo número**.

:::warning
**Atenção**

Ao vincular o número na Cloud API, você não poderá mais utilizá-lo no aplicativo do WhatsApp. Essa é uma regra da Meta, não da Persua.
:::

[PRINT 03 → arraste: assets/conexao-whatsapp-cloud-api/print-03.png]

Na tela de parceria, clique em **Entrar com Facebook** para iniciar o onboarding oficial.

[PRINT 04 → arraste: assets/conexao-whatsapp-cloud-api/print-04.png]

---

## Passo 3. Autenticação no Facebook

Realize o login na conta do Facebook que administra seu Gerenciador de Negócios.

[PRINT 05 → arraste: assets/conexao-whatsapp-cloud-api/print-05.png]

Confirme o acesso ao aplicativo **Hunion** (nome da integração oficial homologada pela Meta que opera a conexão).

[PRINT 06 → arraste: assets/conexao-whatsapp-cloud-api/print-06.png]

---

## Passo 4. Dados empresariais

Selecione o **Portfólio Empresarial** correspondente e confira os dados da empresa (nome, site e país). Clique em **Avançar**.

[PRINT 07 → arraste: assets/conexao-whatsapp-cloud-api/print-07.png]

---

## Passo 5. Informar o número

Informe o código do país (**BR +55**) e insira o número que deseja conectar.

[PRINT 08 → arraste: assets/conexao-whatsapp-cloud-api/print-08.png]

---

## Passo 6. Código de verificação da Meta

A Meta enviará um código para o aplicativo do WhatsApp associado ao número. Insira o código recebido e clique em **Avançar**.

[PRINT 09 → arraste: assets/conexao-whatsapp-cloud-api/print-09.png]

---

## Passo 7. Display Name e fuso horário

Confirme o **Display Name** (nome que aparecerá para seus clientes) e o **fuso horário** da conta. Clique em **Avançar**.

[PRINT 10 → arraste: assets/conexao-whatsapp-cloud-api/print-10.png]

---

## Passo 8. Código de verificação da WABA

Escolha o método de recebimento do código de verificação: **SMS** ou **Ligação Telefônica**.

[PRINT 11 → arraste: assets/conexao-whatsapp-cloud-api/print-11.png]

Após receber o código, insira no campo correspondente e clique em **Verificar** pra finalizar a criação da sua WABA.

[PRINT 12 → arraste: assets/conexao-whatsapp-cloud-api/print-12.png]

---

## Passo 9. Forma de pagamento

A Meta exige uma forma de pagamento cadastrada para operar a Cloud API (o custo é cobrado pela Meta, não pela Persua). Clique em **Adicionar forma de pagamento** e conclua o cadastro.

[PRINT 13 → arraste: assets/conexao-whatsapp-cloud-api/print-13.png]

Após finalizar o cadastro, volte à tela da Persua e clique em **Continuar**.

[PRINT 14 → arraste: assets/conexao-whatsapp-cloud-api/print-14.png]

---

## Passo 10. Selecionar o número integrado

Na tela final, selecione o número que está integrando e clique em **Continuar**.

[PRINT 15 → arraste: assets/conexao-whatsapp-cloud-api/print-15.png]

---

## Passo 11. Finalizar

Clique em **Finalizar** para concluir o processo.

[PRINT 16 → arraste: assets/conexao-whatsapp-cloud-api/print-16.png]

---

## Pronto

Seu número está conectado à Persua via WhatsApp Cloud API. A partir daqui, todas as mensagens passam pela infraestrutura oficial da Meta, com estabilidade e rastreabilidade completa.

---

## Considerações finais

### O que muda no seu WhatsApp Business

- O número **não poderá mais ser usado no aplicativo WhatsApp Business** enquanto estiver conectado à API
- Todos os dispositivos conectados via **WhatsApp Web** serão desconectados (podem ser reconectados depois)
- Não é mais possível **editar ou excluir mensagens** enviadas
- Recursos como **mensagens que desaparecem** e **visualização única** ficam indisponíveis

### Limitações técnicas da Cloud API

- **WhatsApp Desktop para Windows não é compatível** com Cloud API. Mensagens enviadas e recebidas pelo desktop deixarão de funcionar
- **Sincronização de contatos e histórico antigo não é feita** no momento da conexão
- Algumas funcionalidades nativas do app não são suportadas: **Canais, Status, Grupos, enquetes, eventos e localização em tempo real**
- Após reiniciar conversa com um contato pelo app, é necessário aguardar ele responder para continuar pela Persua
- Uso de modelos de mensagem e janela de conversa seguem as regras da API Oficial da Meta

### Boas práticas para manter a conexão saudável

- Use o **WhatsApp Business pelo menos uma vez a cada 15 dias** (em um aparelho homologado) para manter o vínculo ativo
- O número pode ser **vinculado e desvinculado** a qualquer momento pela Persua
- **Não tente usar o mesmo número simultaneamente** no app e na API, a Meta bloqueia

---

### Documentação oficial

Para referência técnica completa, consulte a [documentação oficial da Meta](https://developers.facebook.com/docs/whatsapp/embedded-signup/custom-flows/onboarding-business-app-users) sobre o processo de Embedded Signup.

---

### Próximos passos

:::info
**Continue sua configuração:**

- Configurar equipe e permissões de atendimento
- Criar o primeiro modelo de mensagem
- Conectar um segundo canal (Instagram ou Messenger)
:::
