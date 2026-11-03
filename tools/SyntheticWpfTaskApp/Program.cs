using System.Windows;
using System.Windows.Automation;
using System.Windows.Controls;

namespace SyntheticWpfTaskApp;

internal static class Program
{
    [STAThread]
    private static void Main()
    {
        var panel = new StackPanel { Margin = new Thickness(20) };
        panel.Children.Add(new TextBlock { Text = "Somente dados ficticios. Este aplicativo nao inicia coleta.", Margin = new Thickness(0, 0, 0, 15) });
        panel.Children.Add(new TextBox { Text = "PROCESSO-FICTICIO-001", Margin = new Thickness(0, 5, 0, 5) });
        panel.Children.Add(new TextBlock { Text = "Senha ficticia: foco deve ser excluido." });
        panel.Children.Add(new PasswordBox { Password = "SENHA-FICTICIA-NAO-COLETAR", Margin = new Thickness(0, 5, 0, 15) });
        var check = new CheckBox { Content = "Conferido (ficticio)", Margin = new Thickness(0, 5, 0, 15) };
        AutomationProperties.SetAutomationId(check, "synthetic_check");
        panel.Children.Add(check);
        var status = new TextBlock { Text = "Nenhuma operacao efetuada." };
        foreach (var item in new[] { ("synthetic_save", "Salvar ficticio"), ("synthetic_review", "Revisar ficticio") }) {
            var button = new Button { Content = item.Item2, Margin = new Thickness(0, 5, 0, 5), Height = 35 };
            AutomationProperties.SetAutomationId(button, item.Item1);
            button.Click += (_, _) => status.Text = "Operacao ficticia concluida apenas na memoria.";
            panel.Children.Add(button);
        }
        panel.Children.Add(status);
        new Application().Run(new Window {
            Title = "Observador - Aplicativo ficticio WPF", Width = 620, Height = 430,
            WindowStartupLocation = WindowStartupLocation.CenterScreen, Content = panel
        });
    }
}
