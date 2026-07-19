import javax.swing.*;
import java.awt.*;
import java.awt.event.*;
import java.io.*;
import java.net.*;
import javax.swing.border.TitledBorder;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

public class ClienteEcosistemaJava extends JFrame {
    private Socket socket;
    private PrintWriter out;
    private BufferedReader in;
    private boolean conectado = false;

    private JLabel lblEstadoConexion, lblLDR, lblBuzzer, lblLED;
    private JTextArea txtLog;
    private JButton btnActivar, btnDesactivar, btnAuto;
    private BarraNivel barraNivel;

    private static final String SERVER_IP = "127.0.0.1";
    private static final int SERVER_PORT = 5000;

    public ClienteEcosistemaJava() {
        setTitle("Control de Ecosistema - Java");
        setSize(560, 640);
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setLayout(new BorderLayout(10, 10));
        setLocationRelativeTo(null);

        crearInterfaz();
        conectarServidor();
    }

    private void crearInterfaz() {
        // ---- Panel izquierdo: medidor de luz ----
        barraNivel = new BarraNivel();
        JPanel panelMedidor = new JPanel(new BorderLayout());
        panelMedidor.setBorder(new TitledBorder("Nivel de luz"));
        panelMedidor.add(barraNivel, BorderLayout.CENTER);
        panelMedidor.setPreferredSize(new Dimension(110, 400));
        add(panelMedidor, BorderLayout.WEST);

        // ---- Panel derecho: estado + controles + log ----
        JPanel panelDerecho = new JPanel(new BorderLayout(10, 10));

        JPanel panelEstado = new JPanel(new GridLayout(4, 1, 5, 5));
        panelEstado.setBorder(new TitledBorder("Estado Actual"));
        panelEstado.setPreferredSize(new Dimension(400, 150));

        lblEstadoConexion = new JLabel("Estado: Desconectado");
        lblEstadoConexion.setForeground(Color.ORANGE);
        panelEstado.add(lblEstadoConexion);

        lblLDR = new JLabel("Luz: -- lux");
        panelEstado.add(lblLDR);

        lblBuzzer = new JLabel("Buzzer: APAGADO");
        lblBuzzer.setForeground(Color.RED);
        panelEstado.add(lblBuzzer);

        lblLED = new JLabel("LED: APAGADO");
        lblLED.setForeground(Color.RED);
        panelEstado.add(lblLED);

        panelDerecho.add(panelEstado, BorderLayout.NORTH);

        JPanel panelControl = new JPanel(new FlowLayout(FlowLayout.CENTER, 20, 20));
        panelControl.setBorder(new TitledBorder("Control Manual"));

        btnActivar = new JButton("Activar Alarma");
        btnActivar.setBackground(new Color(144, 238, 144));
        btnActivar.addActionListener(e -> enviarComando("BUZZER_ON"));
        panelControl.add(btnActivar);

        btnDesactivar = new JButton("Desactivar Alarma");
        btnDesactivar.setBackground(new Color(255, 182, 193));
        btnDesactivar.addActionListener(e -> enviarComando("BUZZER_OFF"));
        panelControl.add(btnDesactivar);

        btnAuto = new JButton("↺ Modo Automático");
        btnAuto.addActionListener(e -> enviarComando("AUTO"));
        panelControl.add(btnAuto);

        panelDerecho.add(panelControl, BorderLayout.CENTER);

        JPanel panelLog = new JPanel(new BorderLayout());
        panelLog.setBorder(new TitledBorder("Historial de Eventos"));

        txtLog = new JTextArea(10, 40);
        txtLog.setEditable(false);
        txtLog.setFont(new Font("Monospaced", Font.PLAIN, 12));
        JScrollPane scrollPane = new JScrollPane(txtLog);
        panelLog.add(scrollPane, BorderLayout.CENTER);

        panelDerecho.add(panelLog, BorderLayout.SOUTH);

        add(panelDerecho, BorderLayout.CENTER);
    }

    private void conectarServidor() {
        new Thread(() -> {
            try {
                socket = new Socket(SERVER_IP, SERVER_PORT);
                out = new PrintWriter(socket.getOutputStream(), true);
                in = new BufferedReader(new InputStreamReader(socket.getInputStream()));
                conectado = true;

                SwingUtilities.invokeLater(() -> {
                    lblEstadoConexion.setText("Estado: Conectado");
                    lblEstadoConexion.setForeground(Color.GREEN);
                    agregarLog("Conectado al servidor");
                });

                while (conectado) {
                    String linea = in.readLine();
                    if (linea == null) break;
                    procesarMensaje(linea);
                }
            } catch (Exception e) {
                SwingUtilities.invokeLater(() -> {
                    lblEstadoConexion.setText("Error: " + e.getMessage());
                    lblEstadoConexion.setForeground(Color.RED);
                    agregarLog("Error de conexion: " + e.getMessage());
                });
            }

            conectado = false;
            try {
                if (socket != null) socket.close();
            } catch (IOException e) {}

            try { Thread.sleep(3000); } catch (InterruptedException e) {}
            conectarServidor();
        }).start();
    }

    private void procesarMensaje(String mensaje) {
        try {
            JsonObject json = JsonParser.parseString(mensaje).getAsJsonObject();
            if ("ESTADO".equals(json.get("tipo").getAsString())) {
                double valorLDR = json.get("valor_ldr").getAsDouble();
                String buzzer = json.get("buzzer").getAsString();
                String led = json.get("led").getAsString();

                SwingUtilities.invokeLater(() -> {
                    lblLDR.setText(String.format("Luz: %.1f lux", valorLDR));
                    barraNivel.setValor(valorLDR);

                    if ("ON".equals(buzzer)) {
                        lblBuzzer.setText("Buzzer: ENCENDIDO");
                        lblBuzzer.setForeground(Color.GREEN);
                        lblLED.setText("LED: ENCENDIDO");
                        lblLED.setForeground(Color.GREEN);
                    } else {
                        lblBuzzer.setText("Buzzer: APAGADO");
                        lblBuzzer.setForeground(Color.RED);
                        lblLED.setText("LED: APAGADO");
                        lblLED.setForeground(Color.RED);
                    }

                    agregarLog(String.format("Luz: %.1f lux | Buzzer: %s", valorLDR, buzzer));
                });
            }
        } catch (Exception e) {
            // Ignorar errores de parsing
        }
    }

    private void enviarComando(String comando) {
        if (!conectado) {
            agregarLog("No conectado al servidor");
            return;
        }

        new Thread(() -> {
            try {
                out.println(comando);
                SwingUtilities.invokeLater(() -> agregarLog("Comando enviado: " + comando));
            } catch (Exception e) {
                SwingUtilities.invokeLater(() -> agregarLog("Error: " + e.getMessage()));
            }
        }).start();
    }

    private void agregarLog(String mensaje) {
        txtLog.append(mensaje + "\n");
        txtLog.setCaretPosition(txtLog.getDocument().getLength());
    }

    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> {
            new ClienteEcosistemaJava().setVisible(true);
        });
    }
}

/**
 * Medidor vertical del nivel de luz en lux.
 * Mismo concepto que la página web: degradado noche -> día,
 * con una línea que marca el umbral de alarma (UMBRAL_ALARMA).
 */
class BarraNivel extends JPanel {
    private static final int MAX_LDR = 50;   // debe coincidir con LUX_BRILLANTE del sketch (el ESP32 nunca reporta más que esto)
    private static final int UMBRAL_ALARMA = 15;   // debe coincidir con UMBRAL_LUX del sketch

    private double valor = 0;

    public BarraNivel() {
        setPreferredSize(new Dimension(60, 320));
        setOpaque(true);
    }

    public void setValor(double valor) {
        this.valor = Math.max(0, Math.min(MAX_LDR, valor));
        repaint();
    }

    @Override
    protected void paintComponent(Graphics g) {
        super.paintComponent(g);
        Graphics2D g2 = (Graphics2D) g;
        g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);

        int w = getWidth();
        int h = getHeight();
        int margen = 6;
        int trackX = margen;
        int trackW = w - margen * 2;
        int trackH = h - margen * 2;

        // Fondo del track (noche)
        g2.setColor(new Color(13, 20, 32));
        g2.fillRoundRect(trackX, margen, trackW, trackH, trackW, trackW);

        // Relleno con degradado noche -> día, según el valor actual
        double pct = valor / (double) MAX_LDR;
        int fillH = (int) Math.round(trackH * pct);
        if (fillH > 0) {
            GradientPaint degradado = new GradientPaint(
                    0, margen + trackH, new Color(74, 111, 165),   // noche (abajo)
                    0, margen, new Color(244, 184, 96)             // día (arriba)
            );
            g2.setPaint(degradado);
            g2.fillRoundRect(trackX, margen + trackH - fillH, trackW, fillH, trackW, trackW);
        }

        // Línea de umbral de alarma
        int yUmbral = margen + trackH - Math.round(trackH * (UMBRAL_ALARMA / (float) MAX_LDR));
        g2.setColor(new Color(232, 115, 92));
        g2.fillRect(trackX - 2, yUmbral - 1, trackW + 4, 2);

        // Marcador (círculo) en el nivel actual
        int yMarcador = margen + trackH - fillH;
        g2.setColor(Color.WHITE);
        g2.fillOval(w / 2 - 8, yMarcador - 8, 16, 16);

        // Valor numérico
        g2.setColor(Color.WHITE);
        g2.setFont(new Font("Monospaced", Font.BOLD, 13));
        String texto = String.format("%.0f", valor);
        FontMetrics fm = g2.getFontMetrics();
        g2.drawString(texto, (w - fm.stringWidth(texto)) / 2, h - 4);
    }
}