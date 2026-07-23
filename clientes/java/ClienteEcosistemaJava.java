import javax.swing.*;
import javax.swing.border.TitledBorder;
import java.awt.*;
import java.awt.event.WindowAdapter;
import java.awt.event.WindowEvent;
import java.io.*;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class ClienteEcosistemaJava extends JFrame {
    private static final String SERVER_IP = System.getenv().getOrDefault("ECOSISTEMA_HOST", "127.0.0.1");
    private static final int SERVER_PORT = Integer.parseInt(System.getenv().getOrDefault("ECOSISTEMA_PORT", "5000"));

    private final Object bloqueoSalida = new Object();
    private volatile boolean ejecutando = true;
    private volatile boolean conectado = false;
    private Socket socket;
    private PrintWriter out;

    private JLabel lblEstadoConexion;
    private JLabel lblLDR;
    private JLabel lblADC;
    private JLabel lblBuzzer;
    private JLabel lblLED;
    private JLabel lblModo;
    private JTextArea txtLog;
    private JButton btnActivar;
    private JButton btnDesactivar;
    private JButton btnAuto;
    private BarraNivel barraNivel;

    public ClienteEcosistemaJava() {
        setTitle("Control de Ecosistema - Java");
        setSize(650, 680);
        setDefaultCloseOperation(JFrame.DO_NOTHING_ON_CLOSE);
        setLayout(new BorderLayout(10, 10));
        setLocationRelativeTo(null);

        crearInterfaz();
        addWindowListener(new WindowAdapter() {
            @Override
            public void windowClosing(WindowEvent e) {
                cerrar();
            }
        });

        Thread hiloConexion = new Thread(this::administrarConexion, "conexion-servidor");
        hiloConexion.setDaemon(true);
        hiloConexion.start();
    }

    private void crearInterfaz() {
        JLabel titulo = new JLabel("🌿 Control de Ecosistema", SwingConstants.CENTER);
        titulo.setFont(new Font("SansSerif", Font.BOLD, 22));
        titulo.setBorder(BorderFactory.createEmptyBorder(12, 8, 4, 8));
        add(titulo, BorderLayout.NORTH);

        JPanel contenido = new JPanel(new BorderLayout(12, 12));
        contenido.setBorder(BorderFactory.createEmptyBorder(8, 12, 12, 12));

        barraNivel = new BarraNivel();
        JPanel panelMedidor = new JPanel(new BorderLayout());
        panelMedidor.setBorder(new TitledBorder("Nivel de luz"));
        panelMedidor.add(barraNivel, BorderLayout.CENTER);
        JLabel umbral = new JLabel("Umbral: 15 lux", SwingConstants.CENTER);
        panelMedidor.add(umbral, BorderLayout.SOUTH);
        panelMedidor.setPreferredSize(new Dimension(130, 420));
        contenido.add(panelMedidor, BorderLayout.WEST);

        JPanel panelDerecho = new JPanel(new BorderLayout(10, 10));
        JPanel panelEstado = new JPanel(new GridLayout(6, 1, 5, 5));
        panelEstado.setBorder(new TitledBorder("Estado actual"));
        panelEstado.setPreferredSize(new Dimension(440, 190));

        lblEstadoConexion = new JLabel("Estado: Desconectado");
        lblEstadoConexion.setForeground(Color.ORANGE);
        lblLDR = new JLabel("Luz: -- lux");
        lblADC = new JLabel("ADC: --");
        lblBuzzer = new JLabel("Buzzer: APAGADO");
        lblBuzzer.setForeground(Color.RED);
        lblLED = new JLabel("LED: APAGADO");
        lblLED.setForeground(Color.RED);
        lblModo = new JLabel("Modo: AUTO");

        panelEstado.add(lblEstadoConexion);
        panelEstado.add(lblLDR);
        panelEstado.add(lblADC);
        panelEstado.add(lblBuzzer);
        panelEstado.add(lblLED);
        panelEstado.add(lblModo);
        panelDerecho.add(panelEstado, BorderLayout.NORTH);

        JPanel panelControl = new JPanel(new GridLayout(3, 1, 8, 8));
        panelControl.setBorder(new TitledBorder("Control de actuadores"));
        btnActivar = new JButton("🔊 Activar alarma");
        btnDesactivar = new JButton("🔇 Desactivar alarma");
        btnAuto = new JButton("↺ Modo automático");
        btnActivar.addActionListener(e -> enviarComando("BUZZER_ON"));
        btnDesactivar.addActionListener(e -> enviarComando("BUZZER_OFF"));
        btnAuto.addActionListener(e -> enviarComando("AUTO"));
        panelControl.add(btnActivar);
        panelControl.add(btnDesactivar);
        panelControl.add(btnAuto);
        panelDerecho.add(panelControl, BorderLayout.CENTER);

        JPanel panelLog = new JPanel(new BorderLayout());
        panelLog.setBorder(new TitledBorder("Historial de eventos"));
        txtLog = new JTextArea(12, 38);
        txtLog.setEditable(false);
        txtLog.setFont(new Font("Monospaced", Font.PLAIN, 12));
        panelLog.add(new JScrollPane(txtLog), BorderLayout.CENTER);
        panelDerecho.add(panelLog, BorderLayout.SOUTH);

        contenido.add(panelDerecho, BorderLayout.CENTER);
        add(contenido, BorderLayout.CENTER);
        actualizarControles(false);
    }

    private void administrarConexion() {
        while (ejecutando) {
            try (Socket nuevoSocket = new Socket()) {
                SwingUtilities.invokeLater(() -> actualizarConexion("Conectando...", Color.ORANGE));
                nuevoSocket.connect(new InetSocketAddress(SERVER_IP, SERVER_PORT), 4000);
                nuevoSocket.setKeepAlive(true);

                synchronized (bloqueoSalida) {
                    socket = nuevoSocket;
                    out = new PrintWriter(new OutputStreamWriter(socket.getOutputStream(), StandardCharsets.UTF_8), true);
                }
                conectado = true;
                SwingUtilities.invokeLater(() -> {
                    actualizarConexion("Conectado a " + SERVER_IP + ":" + SERVER_PORT, new Color(0, 140, 0));
                    actualizarControles(true);
                    agregarLog("Conectado al servidor");
                });

                try (BufferedReader in = new BufferedReader(new InputStreamReader(nuevoSocket.getInputStream(), StandardCharsets.UTF_8))) {
                    String linea;
                    while (ejecutando && (linea = in.readLine()) != null) {
                        procesarMensaje(linea);
                    }
                }
            } catch (IOException e) {
                if (ejecutando) {
                    SwingUtilities.invokeLater(() -> agregarLog("Conexión: " + e.getMessage()));
                }
            } finally {
                conectado = false;
                synchronized (bloqueoSalida) {
                    out = null;
                    socket = null;
                }
                SwingUtilities.invokeLater(() -> {
                    actualizarConexion("Desconectado; reintentando...", Color.RED);
                    actualizarControles(false);
                });
            }

            if (ejecutando) {
                try {
                    Thread.sleep(3000);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    break;
                }
            }
        }
    }

    private void procesarMensaje(String mensaje) {
        if (!"ESTADO".equals(extraerCadena(mensaje, "tipo", ""))) return;

        double lux = extraerNumero(mensaje, "valor_ldr", 0.0);
        int adc = (int) Math.round(extraerNumero(mensaje, "adc", 0));
        String buzzer = extraerCadena(mensaje, "buzzer", "OFF");
        String led = extraerCadena(mensaje, "led", "OFF");
        String modo = extraerCadena(mensaje, "modo", "AUTO");
        String timestamp = extraerCadena(mensaje, "timestamp", "");

        SwingUtilities.invokeLater(() -> {
            lblLDR.setText(String.format("Luz: %.1f lux", lux));
            lblADC.setText("ADC: " + adc);
            lblBuzzer.setText("Buzzer: " + ("ON".equals(buzzer) ? "ENCENDIDO 🔔" : "APAGADO 🔕"));
            lblBuzzer.setForeground("ON".equals(buzzer) ? new Color(0, 140, 0) : Color.RED);
            lblLED.setText("LED: " + ("ON".equals(led) ? "ENCENDIDO 💡" : "APAGADO ⚫"));
            lblLED.setForeground("ON".equals(led) ? new Color(0, 140, 0) : Color.RED);
            lblModo.setText("Modo: " + modo);
            barraNivel.setValor(lux);
            agregarLog(String.format("[%s] Luz %.1f lux | ADC %d | Alarma %s | %s",
                    timestamp.length() >= 19 ? timestamp.substring(0, 19) : timestamp, lux, adc, buzzer, modo));
        });
    }

    private static String extraerCadena(String json, String clave, String respaldo) {
        Pattern patron = Pattern.compile("\\\"" + Pattern.quote(clave) + "\\\"\\s*:\\s*\\\"([^\\\"]*)\\\"");
        Matcher matcher = patron.matcher(json);
        return matcher.find() ? matcher.group(1) : respaldo;
    }

    private static double extraerNumero(String json, String clave, double respaldo) {
        Pattern patron = Pattern.compile("\\\"" + Pattern.quote(clave) + "\\\"\\s*:\\s*(-?\\d+(?:\\.\\d+)?)");
        Matcher matcher = patron.matcher(json);
        if (!matcher.find()) return respaldo;
        try {
            return Double.parseDouble(matcher.group(1));
        } catch (NumberFormatException e) {
            return respaldo;
        }
    }

    private void enviarComando(String comando) {
        if (!conectado) {
            agregarLog("No hay conexión con el servidor");
            return;
        }
        synchronized (bloqueoSalida) {
            if (out != null) {
                out.println(comando);
                if (out.checkError()) {
                    agregarLog("Error al enviar " + comando);
                } else {
                    agregarLog("Comando enviado: " + comando);
                }
            }
        }
    }

    private void actualizarConexion(String texto, Color color) {
        lblEstadoConexion.setText("Estado: " + texto);
        lblEstadoConexion.setForeground(color);
    }

    private void actualizarControles(boolean habilitados) {
        btnActivar.setEnabled(habilitados);
        btnDesactivar.setEnabled(habilitados);
        btnAuto.setEnabled(habilitados);
    }

    private void agregarLog(String mensaje) {
        txtLog.append(mensaje + System.lineSeparator());
        txtLog.setCaretPosition(txtLog.getDocument().getLength());
    }

    private void cerrar() {
        ejecutando = false;
        conectado = false;
        synchronized (bloqueoSalida) {
            if (socket != null) {
                try {
                    socket.close();
                } catch (IOException ignored) {
                }
            }
        }
        dispose();
    }

    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> new ClienteEcosistemaJava().setVisible(true));
    }
}

class BarraNivel extends JPanel {
    private static final int MAX_LDR = 50;
    private static final int UMBRAL_ALARMA = 15;
    private double valor = 0;

    public BarraNivel() {
        setPreferredSize(new Dimension(75, 350));
        setOpaque(true);
    }

    public void setValor(double valor) {
        this.valor = Math.max(0, Math.min(MAX_LDR, valor));
        repaint();
    }

    @Override
    protected void paintComponent(Graphics g) {
        super.paintComponent(g);
        Graphics2D g2 = (Graphics2D) g.create();
        g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);

        int w = getWidth();
        int h = getHeight();
        int margen = 8;
        int trackX = margen;
        int trackW = w - margen * 2;
        int trackH = h - margen * 2;

        g2.setColor(new Color(13, 20, 32));
        g2.fillRoundRect(trackX, margen, trackW, trackH, trackW, trackW);

        double porcentaje = valor / MAX_LDR;
        int fillH = (int) Math.round(trackH * porcentaje);
        if (fillH > 0) {
            GradientPaint degradado = new GradientPaint(0, margen + trackH, new Color(74, 111, 165),
                    0, margen, new Color(244, 184, 96));
            g2.setPaint(degradado);
            g2.fillRoundRect(trackX, margen + trackH - fillH, trackW, fillH, trackW, trackW);
        }

        int yUmbral = margen + trackH - Math.round(trackH * (UMBRAL_ALARMA / (float) MAX_LDR));
        g2.setColor(new Color(232, 115, 92));
        g2.fillRect(trackX - 2, yUmbral - 1, trackW + 4, 3);

        int yMarcador = margen + trackH - fillH;
        g2.setColor(Color.WHITE);
        g2.fillOval(w / 2 - 8, yMarcador - 8, 16, 16);

        g2.setFont(new Font("Monospaced", Font.BOLD, 12));
        String texto = String.format("%.1f", valor);
        FontMetrics fm = g2.getFontMetrics();
        g2.drawString(texto, (w - fm.stringWidth(texto)) / 2, h - 5);
        g2.dispose();
    }
}
