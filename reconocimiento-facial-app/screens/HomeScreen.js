import React, { useState, useEffect } from 'react';
import { View, Text, Button, Image, StyleSheet, ActivityIndicator, Alert, ScrollView } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { reconocerUsuario } from '../services/api';

const HomeScreen = ({ navigation }) => {
  const [imagen, setImagen] = useState(null);
  const [resultado, setResultado] = useState(null);
  const [cargando, setCargando] = useState(false);

  useEffect(() => {
    (async () => {
      const { status } = await ImagePicker.requestCameraPermissionsAsync();
      if (status !== 'granted') {
        alert('Se requieren permisos de cámara para esta función.');
      }
    })();
  }, []);

  const seleccionarImagen = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 1,
    });
    if (!result.canceled) {
      const foto = result.assets[0];
      setImagen(foto);
      enviarAlBackend(foto);
    }
  };

  const tomarFoto = async () => {
    const result = await ImagePicker.launchCameraAsync({
      quality: 1,
      allowsEditing: false,
    });
    if (!result.canceled) {
      const foto = result.assets[0];
      setImagen(foto);
      enviarAlBackend(foto);
    }
  };

  const enviarAlBackend = async (foto) => {
    try {
      setCargando(true);
      const res = await reconocerUsuario(foto);
      setResultado(res);
    } catch (err) {
      console.log('Error:', err);
      Alert.alert('Error', 'No se pudo conectar con el servidor.');
    } finally {
      setCargando(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Reconocimiento Facial</Text>
      <Button title="Registrar Nuevo Usuario" onPress={() => navigation.navigate('Registro')} />
      <View style={{ marginVertical: 10 }} />
      <Button title="Seleccionar Imagen de Galería" onPress={seleccionarImagen} />
      <View style={{ marginVertical: 10 }} />
      <Button title="Tomar Foto con Cámara" onPress={tomarFoto} />

      {cargando && <ActivityIndicator size="large" color="#007AFF" style={{ marginTop: 20 }} />}

      {resultado && (
        <View style={styles.resultado}>
          {resultado.mensaje ? (
            <Text style={styles.alerta}>{resultado.mensaje}</Text>
          ) : (
            <>
              <Text style={styles.texto}>
                Detectado: {resultado.nombre} {resultado.apellido}
              </Text>
              <Text>Código único: {resultado.codigo_unico}</Text>
              {resultado.similitud_tradicional_promedio && (
                <Text>Similitud tradicional: {resultado.similitud_tradicional_promedio}</Text>
              )}
              {resultado.similitud_face_recognition_promedio && (
                <Text>Similitud FR: {resultado.similitud_face_recognition_promedio}</Text>
              )}
              {resultado.alerta && (
                <Text style={styles.alerta}>
                  ⚠️ {resultado.mensaje_alerta}
                </Text>
              )}
              <Image
                source={{ uri: `http://192.168.10.107:5000/uploads/${resultado.imagen_referencia}` }}
                style={styles.imagen}
              />
            </>
          )}
        </View>
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { flexGrow: 1, alignItems: 'center', paddingTop: 40, backgroundColor: "#fff" },
  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 20 },
  texto: { fontSize: 18, marginVertical: 10 },
  alerta: { fontSize: 16, color: 'red', marginVertical: 10 },
  imagen: { width: 200, height: 200, marginTop: 10, borderRadius: 10 },
  resultado: { marginTop: 30, alignItems: 'center' },
});

export default HomeScreen;

