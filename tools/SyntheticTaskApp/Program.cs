using System;
using System.Drawing;
using System.Windows.Forms;

namespace SyntheticTaskApp;

internal static class Program
{
    [STAThread]
    private static void Main()
    {
        ApplicationConfiguration.Initialize();
        Application.Run(new FictionalForm());
    }
}

internal sealed class FictionalForm : Form
{
    private readonly Label _status;

    public FictionalForm()
    {
        Text = "Observador - Aplicativo ficticio";
        StartPosition = FormStartPosition.CenterScreen;
        Size = new Size(600, 370);
        MinimumSize = new Size(550, 340);

        var notice = new Label
        {
            Text = "Somente dados ficticios. Nada e salvo, transmitido ou enviado.",
            Location = new Point(20, 20),
            AutoSize = true
        };
        var caseLabel = new Label { Text = "Codigo ficticio", Location = new Point(20, 65), AutoSize = true };
        var caseInput = new TextBox
        {
            Name = "synthetic_case",
            Text = "PROCESSO-FICTICIO-001",
            Location = new Point(20, 90),
            Width = 360
        };
        var passwordLabel = new Label
        {
            Text = "Campo de senha de teste (deve ser excluido)",
            Location = new Point(20, 130),
            AutoSize = true
        };
        var passwordInput = new TextBox
        {
            Name = "synthetic_password",
            Text = "SENHA-FICTICIA-NAO-COLETAR",
            UseSystemPasswordChar = true,
            Location = new Point(20, 155),
            Width = 360
        };
        var checkBox = new CheckBox
        {
            Text = "Conferido (ficticio)",
            Location = new Point(20, 197),
            AutoSize = true
        };
        var save = new Button { Name = "synthetic_save", Text = "Salvar ficticio", Location = new Point(20, 238), Width = 160 };
        var review = new Button { Name = "synthetic_review", Text = "Revisar ficticio", Location = new Point(195, 238), Width = 160 };
        _status = new Label
        {
            Text = "Nenhuma operacao efetuada.",
            Location = new Point(20, 287),
            Width = 510,
            AutoSize = false,
            Height = 35
        };
        save.Click += (_, _) => _status.Text = "Operacao ficticia concluida apenas na memoria.";
        review.Click += (_, _) => _status.Text = "Revisao ficticia concluida apenas na memoria.";

        Controls.AddRange(new Control[]
        {
            notice, caseLabel, caseInput, passwordLabel, passwordInput,
            checkBox, save, review, _status
        });
    }
}
