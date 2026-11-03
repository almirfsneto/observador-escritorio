# Manual lab fixture only: does not observe other applications or save data.
Add-Type -AssemblyName System.Windows.Forms
$form = New-Object System.Windows.Forms.Form
$form.Text = 'Observador - somente dados ficticios'
$form.Width = 520
$form.Height = 260
$notice = New-Object System.Windows.Forms.Label
$notice.Text = 'Aplicativo ficticio. Este formulario nao inicia coleta.'
$notice.SetBounds(20, 20, 460, 30)
$inputField = New-Object System.Windows.Forms.TextBox
$inputField.Text = 'PROCESSO-FICTICIO-001'
$inputField.SetBounds(20, 60, 300, 25)
$passwordField = New-Object System.Windows.Forms.TextBox
$passwordField.UseSystemPasswordChar = $true
$passwordField.Text = 'SENHA-FICTICIA-NAO-COLETAR'
$passwordField.SetBounds(20, 100, 300, 25)
$button = New-Object System.Windows.Forms.Button
$button.Text = 'Salvar ficticio'
$button.SetBounds(20, 140, 160, 30)
$button.Add_Click({ $notice.Text = 'Registro ficticio salvo apenas na memoria.' })
$form.Controls.AddRange(@($notice, $inputField, $passwordField, $button))
$null = $form.ShowDialog()
$form.Dispose()
